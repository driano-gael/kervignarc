// La fiche des **pauses programmées** d'une étape (E05US033, ADR-0091).
//
// Partagée par les **deux** écrans qui composent des phases — « Composer un déroulé » (un modèle de
// bibliothèque) et « Phases » (le déroulé d'un tournoi) —, comme `ReglageSuisse`, `ReglagePoules` et
// `ReglageBigShootOff` avant elle.
//
// ⚠️ **Ce composant ne détient AUCUN état** (leçon de la revue d'E06US006, reprise telle quelle) :
// monté sous condition, un état dérivé d'une prop diverge dès que la condition bascule.
//
// **Deux réglages sur la même fiche, et c'est délibéré** : le découpage en tours n'a d'existence que
// pour permettre les arrêts (« sans lui, une qualification n'a qu'un tour et ne peut pas s'arrêter en
// cours de route » — CA). Les séparer en deux fieldsets ferait chercher à l'organisateur pourquoi son
// arrêt sur la qualification est refusé, alors que la réponse est juste au-dessus.

import type { EtatArrets, LigneArret, PorteeArret } from './arrets'
import { TOURS_MAX_REGLABLES, decrire, ligneNeuve, toursEnDoublon, versArrets } from './arrets'

/**
 * Rend la fiche des pauses programmées. Aucun état : l'unique source est `etat`, détenu par le parent.
 *
 * `decoupable` dit si le **type** de cette étape tire ses tours d'un réglage d'organisateur — la
 * qualification et l'échauffement — plutôt que de sa structure. C'est le parent qui le sait (il
 * connaît le type choisi), et le champ de découpage disparaît quand c'est faux : l'API le **refuse**
 * sur les autres types (`DecoupageEnToursInvalide`, 422), donc l'offrir serait proposer un geste qui
 * échoue.
 */
export function ReglageArrets({
  etat,
  surChangement,
  decoupable,
}: {
  etat: EtatArrets
  surChangement: (etat: EtatArrets) => void
  decoupable: boolean
}) {
  const doublons = toursEnDoublon(etat)
  const illisible = versArrets(etat) === undefined

  function changerLigne(cle: string, champs: Partial<LigneArret>) {
    surChangement({
      ...etat,
      lignes: etat.lignes.map((ligne) => (ligne.cle === cle ? { ...ligne, ...champs } : ligne)),
    })
  }

  function retirer(cle: string) {
    surChangement({ ...etat, lignes: etat.lignes.filter((ligne) => ligne.cle !== cle) })
  }

  return (
    <fieldset className="deroule__sources">
      <legend>Pauses programmées</legend>

      <p className="carte__aide">
        Par défaut, la salle enchaîne les tours toute seule. Programmez une pause pour l’arrêter à
        un moment choisi — le repas, une réorganisation, une annonce. Un admin la relance d’un
        geste, et la phase repart en automatique jusqu’à la pause suivante.
      </p>

      {/* CA — « la qualification et l'échauffement deviennent divisibles en tours ». Le champ n'est
          offert que là où il a un sens : ailleurs, le nombre de tours vient de la structure du format
          (braquets, round-robin, rondes réglées, manches) et l'API refuse un second réglage. */}
      {decoupable && (
        <>
          <label className="formulaire__libelle">
            Découper en combien de tours&nbsp;?
            <input
              inputMode="numeric"
              placeholder="1"
              value={etat.tours}
              onChange={(e) => surChangement({ ...etat, tours: e.target.value })}
            />
          </label>
          <p className="carte__aide">
            Laissez vide pour une phase d’un seul tenant. «&nbsp;2&nbsp;» découpe par exemple 20
            volées en deux tours de 10 — ce qui permet d’y poser une pause.
          </p>
        </>
      )}

      {etat.lignes.length === 0 ? (
        /* ⚠️ **Pas de `role="status"` ici**, à la différence des deux alertes en bas de fiche. Ce
           texte est **statique** : il décrit le défaut, il n'annonce aucun changement. Le lui donner
           a fait tomber deux tests de `Profondeur.test.tsx`, qui gardent l'invariant « bouton bloqué
           ⟺ un message dit pourquoi » en cherchant `queryByRole('status')` — un état vivant
           permanent rendait la garde inopérante. Le test avait raison, pas la fiche. */
        <p className="carte__aide">
          Aucune pause programmée&nbsp;: la phase se déroulera d’un bout à l’autre sans s’arrêter.
        </p>
      ) : (
        <ul className="deroule__liste">
          {etat.lignes.map((ligne) => (
            <li key={ligne.cle}>
              <label className="formulaire__libelle">
                Après le tour
                <input
                  inputMode="numeric"
                  placeholder="3"
                  value={ligne.apresTour}
                  onChange={(e) => changerLigne(ligne.cle, { apresTour: e.target.value })}
                />
              </label>

              <label className="formulaire__libelle">
                Portée
                <select
                  value={ligne.portee}
                  onChange={(e) =>
                    changerLigne(ligne.cle, { portee: e.target.value as PorteeArret })
                  }
                >
                  <option value="phase">Cette phase seule</option>
                  <option value="depart">Tout le créneau</option>
                </select>
              </label>

              {/* La relecture en clair. L'écran ne peut pas dire **quand** la pause tombera (il
                  ignore le nombre de tours et l'heure) mais il peut dire **ce qu'elle coupera**, et
                  c'est ce que l'organisateur relit avant de valider son planning. */}
              <p className="carte__aide">{decrire(ligne)}</p>

              <button
                type="button"
                className="bouton bouton--discret"
                onClick={() => retirer(ligne.cle)}
              >
                Retirer cette pause
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        type="button"
        className="bouton bouton--discret"
        onClick={() => surChangement({ ...etat, lignes: [...etat.lignes, ligneNeuve()] })}
      >
        Ajouter une pause
      </button>

      {doublons.length > 0 && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Deux pauses sont posées après le même tour ({doublons.join(', ')})&nbsp;: la phase ne peut
          pas s’arrêter deux fois au même endroit.
        </span>
      )}

      {illisible && doublons.length === 0 && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Indiquez pour chaque pause un numéro de tour entier, entre 1 et {TOURS_MAX_REGLABLES}.
        </span>
      )}
    </fieldset>
  )
}
