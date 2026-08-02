// Écran « Écrans de salle » (E07US004) — axe **pilotage**, préparation des écrans d'un tournoi.
//
// Le pendant de « Postes de cible » (E04US001) pour les écrans : créer, nommer, distribuer le code
// de rattachement, régler le déroulé de vues. Deux différences avec les cibles, toutes deux issues
// du modèle :
//
// - la création est **explicite** (aucun plan de salle ne dit combien d'écrans le club branchera,
//   ni où) — d'où un formulaire, là où les cibles ont un bouton « préparer les codes » idempotent ;
// - un écran se **supprime** (il se débranche), une cible non : son code est imprimé sous un QR.
//
// Le **pilotage** (imposer une vue) n'est pas ici mais dans la console de supervision : c'est ce que
// le CA demande, et c'est cohérent — on prépare à froid, on pilote à chaud, sur l'écran où l'on voit
// déjà l'état de la salle.

import { useState } from 'react'

import { MessageErreur } from '../../shared/ui/MessageErreur'
import {
  CADENCE_MAX_S,
  CADENCE_MIN_S,
  LIBELLE_VUE,
  TOUTES_LES_VUES,
  type Ecran,
  type VueEcran,
  type VueProgrammee,
} from './api'
import {
  useCreerEcran,
  useEcrans,
  useReglerDeroule,
  useRenommerEcran,
  useSupprimerEcran,
} from './hooks'

export function Ecrans({ tournoiId }: { tournoiId: number }) {
  const ecrans = useEcrans(tournoiId)

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Écrans de salle</h2>
      <p className="carte__aide">
        Un écran de salle est un <strong>poste</strong>, comme une tablette de cible : on le
        rattache en scannant son code depuis le navigateur de l’écran. Il fait ensuite défiler les
        vues de son déroulé, tout seul, sans que personne n’ait à y toucher. Depuis la console de
        supervision, vous pouvez lui imposer une vue à distance.
      </p>
      <NouvelEcran tournoiId={tournoiId} />
      <MessageErreur erreur={ecrans.error} />
      {ecrans.data === undefined ? (
        <p className="carte__etat">Chargement…</p>
      ) : ecrans.data.length === 0 ? (
        <p className="carte__etat">
          Aucun écran pour ce tournoi. Créez-en un par emplacement (par exemple «&nbsp;près du pas
          de tir&nbsp;» et «&nbsp;côté public&nbsp;») : chacun aura son propre déroulé.
        </p>
      ) : (
        <ul className="liste">
          {ecrans.data.map((ecran) => (
            // La `key` inclut l'**état serveur** : toute mutation invalide la liste, et changer de
            // clé **remonte** la carte, donc réinitialise ses copies locales (nom, déroulé) depuis
            // les props fraîches. C'est le remplaçant recommandé d'un `useEffect` de
            // resynchronisation — et il ferme une perte de mise à jour réelle : après un réglage
            // venu d'un autre poste admin, ou après un 422 sur cadence hors bornes, l'écran gardait
            // l'ancienne valeur et « Enregistrer » l'écrasait en silence (correctif de revue).
            <CarteEcran
              key={`${ecran.id}:${ecran.libelle}:${JSON.stringify(ecran.deroule)}`}
              ecran={ecran}
              tournoiId={tournoiId}
            />
          ))}
        </ul>
      )}
    </section>
  )
}

function NouvelEcran({ tournoiId }: { tournoiId: number }) {
  const [libelle, setLibelle] = useState('')
  const creer = useCreerEcran(tournoiId)

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (libelle.trim() === '') return
    creer.mutate(libelle, { onSuccess: () => setLibelle('') })
  }

  return (
    <form className="formulaire" onSubmit={soumettre}>
      <input
        className="formulaire__champ"
        value={libelle}
        onChange={(e) => setLibelle(e.target.value)}
        placeholder="Où est cet écran ? (ex. près du pas de tir)"
        aria-label="Emplacement de l’écran"
      />
      <button type="submit" disabled={creer.isPending || libelle.trim() === ''}>
        Ajouter un écran
      </button>
      <MessageErreur erreur={creer.error} />
    </form>
  )
}

function CarteEcran({ ecran, tournoiId }: { ecran: Ecran; tournoiId: number }) {
  const renommer = useRenommerEcran(tournoiId)
  const supprimer = useSupprimerEcran(tournoiId)
  const [nom, setNom] = useState(ecran.libelle)

  const demanderSuppression = () => {
    const ok = window.confirm(
      `Retirer l’écran « ${ecran.libelle} » ? Son code cessera de fonctionner et l’écran repassera à l’accueil.`,
    )
    if (ok) supprimer.mutate(ecran.id)
  }

  return (
    <li className="liste__item">
      <div className="formulaire">
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          aria-label={`Emplacement de l’écran ${ecran.libelle}`}
        />
        <button
          type="button"
          disabled={renommer.isPending || nom.trim() === '' || nom === ecran.libelle}
          onClick={() => renommer.mutate({ posteId: ecran.id, libelle: nom })}
        >
          Renommer
        </button>
        {/* Le code est un **secret d'usage** à distribuer, comme celui d'une cible : il s'affiche
            ici (écran admin) et jamais dans la console de supervision, toujours ouverte. */}
        <span className="liste__meta">
          Code&nbsp;: <strong>{ecran.code}</strong>
        </span>
        <button
          type="button"
          className="lien"
          disabled={supprimer.isPending}
          onClick={demanderSuppression}
        >
          Retirer
        </button>
      </div>
      <ReglageDeroule ecran={ecran} tournoiId={tournoiId} />
      <MessageErreur erreur={renommer.error ?? supprimer.error} />
    </li>
  )
}

/** Le déroulé de vues d'un écran : ce qu'il fait tourner et à quelle cadence.
 *
 * On édite une **copie locale** et on enregistre — même parti que l'atelier de composition
 * (E01US024) : le serveur revalide les bornes de cadence (`422 cadence_ecran_invalide`) et reste
 * l'autorité, le front ne fait que ne pas proposer l'absurde. */
function ReglageDeroule({ ecran, tournoiId }: { ecran: Ecran; tournoiId: number }) {
  const [vues, setVues] = useState<VueProgrammee[]>(ecran.deroule)
  const regler = useReglerDeroule(tournoiId)

  const modifier = (index: number, etape: VueProgrammee) =>
    setVues(vues.map((v, i) => (i === index ? etape : v)))
  const retirer = (index: number) => setVues(vues.filter((_, i) => i !== index))
  const ajouter = () => setVues([...vues, { vue: 'classement', cadence_s: 30 }])

  return (
    <div className="ecrans__deroule">
      <span className="carte__soustitre">Déroulé</span>
      {vues.map((etape, index) => (
        // La **position** est la clé, pas la vue : « classement, plan, classement » est un déroulé
        // légitime (la vue qui intéresse le plus revient plus souvent), et deux étapes identiques
        // partageraient sinon la même clé React.
        <span className="ecrans__etape" key={index}>
          <label className="sr-only" htmlFor={`vue-${ecran.id}-${index}`}>
            Vue {index + 1}
          </label>
          <select
            id={`vue-${ecran.id}-${index}`}
            value={etape.vue}
            onChange={(e) => modifier(index, { ...etape, vue: e.target.value as VueEcran })}
          >
            {TOUTES_LES_VUES.map((v) => (
              <option key={v} value={v}>
                {LIBELLE_VUE[v]}
              </option>
            ))}
          </select>
          <label className="sr-only" htmlFor={`cadence-${ecran.id}-${index}`}>
            Cadence de la vue {index + 1}, en secondes
          </label>
          <input
            id={`cadence-${ecran.id}-${index}`}
            type="number"
            min={CADENCE_MIN_S}
            max={CADENCE_MAX_S}
            value={etape.cadence_s}
            onChange={(e) => modifier(index, { ...etape, cadence_s: Number(e.target.value) })}
            style={{ width: '5em' }}
          />
          <span>s</span>
          {vues.length > 1 && (
            <button type="button" className="lien" onClick={() => retirer(index)}>
              ×<span className="sr-only"> retirer la vue {index + 1}</span>
            </button>
          )}
        </span>
      ))}
      <button type="button" className="lien" onClick={ajouter}>
        + Ajouter une vue
      </button>
      <button
        type="button"
        disabled={regler.isPending || vues.length === 0}
        onClick={() => regler.mutate({ posteId: ecran.id, vues })}
      >
        Enregistrer le déroulé
      </button>
      <MessageErreur erreur={regler.error} />
    </div>
  )
}
