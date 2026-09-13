// Surface scoreur de la **qualification** (E16US019) — valider une feuille, annuler une validation.
// C'est la surface annoncée par E04US002 (« validation/correction, §7.3 ») et jamais livrée : le
// backend l'exposait depuis juillet, aucun écran ne l'appelait.

// ⚠️ **La correction ne se fait pas ici** : annuler rouvre la volée sur la **tablette de la
// cible**, qui la ressaisit, puis le scoreur revalide — c'est le parcours du questionnaire S08.
// Le score reste au classement pendant toute cette fenêtre (ADR-0109).

// ⚠️ DETTE-100 : `POST /saisie/corrections` existe côté serveur et pose le rang **scoreur**
// (E16US020), mais aucun écran ne l'appelle — c'est ici qu'on le chercherait.

import { useState } from 'react'
import { useClassement } from '../competition/hooks'
import { ChoixCreneau } from '../departs/ChoixCreneau'
import { creneauRetenu } from '../departs/libelle'
import { useDeparts } from '../departs/hooks'
import { departDeSalle } from '../salle/rotation'
import type { Volee } from '../saisie/api'
import { BoutonConfirme } from '../../shared/ui/BoutonConfirme'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { GesteDuBouton } from './etat'
import { aValider, avertissementAnnulation, etatVolee, gesteDuBouton } from './etat'
import {
  useAnnulerValidation,
  useRefermerCorrection,
  useSerieScoreur,
  useValiderSerie,
} from './hooks'

export function PanneauValidationQualif({ tournoiId }: { tournoiId: number }) {
  const [choixDepart, setChoixDepart] = useState<number | null>(null)
  const [archerId, setArcherId] = useState<number | null>(null)
  const departs = useDeparts(tournoiId)
  const liste = departs.data ?? []
  const departId = creneauRetenu(liste, choixDepart, departDeSalle)
  const classement = useClassement(tournoiId, departId)
  const serie = useSerieScoreur(tournoiId, archerId)
  const valider = useValiderSerie(tournoiId)
  const annuler = useAnnulerValidation(tournoiId)
  const refermer = useRefermerCorrection(tournoiId)

  const lignes = classement.data?.lignes ?? []

  return (
    <section className="carte">
      <h3 className="carte__titre">Validation — qualification</h3>
      <p className="carte__etat">
        Validez la feuille d'un archer, ou annulez une validation pour la faire corriger. Une
        validation annulée rouvre la saisie sur la tablette de la cible ; le score reste au
        classement jusqu'à la ressaisie.
      </p>
      {/* ⚠️ DETTE-052 — ce sélecteur filtre la **liste d'archers**, et rien d'autre : les trois
          appels qu'il déclenche ne transportent aucun `depart_id`, donc le serveur **devine** le
          créneau (le plus petit où l'archer est inscrit). Sur un archer engagé matin et
          après-midi, on peut donc valider la feuille du matin en ayant choisi l'après-midi. La
          résorption est serveur — porter le créneau dans les corps de requête. */}
      <ChoixCreneau
        departs={liste}
        valeur={departId}
        surChangement={(valeur) => {
          setChoixDepart(valeur)
          setArcherId(null)
        }}
        etiquette="Départ à valider"
      />
      <MessageErreur erreur={serie.error ?? valider.error ?? annuler.error ?? refermer.error} />
      {lignes.length === 0 ? (
        <p className="carte__etat">Aucun archer sur ce départ pour l'instant.</p>
      ) : (
        <label className="classement-filtre">
          Archer{' '}
          <select
            value={archerId ?? ''}
            onChange={(evenement) =>
              setArcherId(evenement.target.value === '' ? null : Number(evenement.target.value))
            }
          >
            <option value="">Choisir un archer…</option>
            {lignes.map((ligne) => (
              <option key={ligne.archer_id} value={ligne.archer_id}>
                {ligne.nom} {ligne.prenom}
              </option>
            ))}
          </select>
        </label>
      )}
      {archerId !== null && serie.isSuccess && (
        <FeuilleAValider
          volees={serie.data.volees}
          cumul={serie.data.cumul}
          enCours={valider.isPending || annuler.isPending || refermer.isPending}
          validable={aValider(serie.data)}
          geste={gesteDuBouton(serie.data)}
          avertissement={(numero) => avertissementAnnulation(serie.data, numero)}
          // Deux gestes, deux routes : refermer **nomme** son lot, valider ne nomme rien. La
          // décision vit dans `gesteDuBouton` (pure, testée) — pas ici.
          onValider={(geste) => {
            if (geste.geste === 'refermer') refermer.mutate({ archerId, numero: geste.numero })
            else valider.mutate(archerId)
          }}
          onAnnuler={(numero) => annuler.mutate({ archerId, numero })}
        />
      )}
    </section>
  )
}

function FeuilleAValider({
  volees,
  cumul,
  enCours,
  validable,
  geste,
  avertissement,
  onValider,
  onAnnuler,
}: {
  volees: Volee[]
  cumul: number
  enCours: boolean
  validable: boolean
  /** Ce que le bouton du bas va faire — décidé par `gesteDuBouton`, pas ici. */
  geste: GesteDuBouton
  avertissement: (numero: number) => string
  onValider: (geste: GesteDuBouton) => void
  onAnnuler: (numero: number) => void
}) {
  return (
    <>
      <ul className="validation-liste">
        {volees.map((volee) => (
          <LigneVolee
            key={volee.numero}
            volee={volee}
            enCours={enCours}
            avertissement={avertissement(volee.numero)}
            onAnnuler={() => onAnnuler(volee.numero)}
          />
        ))}
      </ul>
      <p className="carte__etat">
        Total validé : <strong>{cumul}</strong>
      </p>
      {/* ⚠️ Le serveur referme une correction **avant** de valider quoi que ce soit d'autre, un
          lot à la fois : le bouton doit dire lequel des deux gestes il déclenche, sinon il éteint
          le marqueur « En correction » alors qu'on croyait acter des volées fraîches. */}
      <button type="button" disabled={enCours || !validable} onClick={() => onValider(geste)}>
        {geste.geste === 'refermer'
          ? `Refermer la correction — volée${geste.volees.length > 1 ? 's' : ''} ${geste.volees.join(', ')}`
          : 'Valider'}
      </button>
    </>
  )
}

function LigneVolee({
  volee,
  enCours,
  avertissement,
  onAnnuler,
}: {
  volee: Volee
  enCours: boolean
  avertissement: string
  onAnnuler: () => void
}) {
  const etat = etatVolee(volee)

  return (
    <li className="validation-liste__ligne">
      <span className="validation-liste__volee">
        Volée {volee.numero} — {volee.valeurs.join(' ')}
        {etat === 'en_correction' && (
          <span className="validation-liste__badge"> En correction</span>
        )}
      </span>
      <span className="validation-liste__actions">
        {etat === 'validee' ? (
          <BoutonConfirme
            libelle="Annuler la validation"
            className="lien"
            titre={`Annuler la validation de la volée ${volee.numero} ?`}
            message={avertissement}
            libelleConfirmer="Annuler la validation"
            disabled={enCours}
            enCours={enCours}
            onConfirmer={onAnnuler}
          />
        ) : (
          <span className="carte__etat">
            {etat === 'en_correction' ? 'À ressaisir sur la tablette' : 'Non validée'}
          </span>
        )}
      </span>
    </li>
  )
}
