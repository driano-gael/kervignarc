// Panneau scoreur des forfaits de **qualification** (E04US015, ADR-0050).
//
// C'est l'alternative désignée à la suppression d'archer (E02US003, ADR-0016) : un archer qui
// abandonne ou est disqualifié n'est **pas** effacé — ses flèches sont préservées, il est seulement
// statué. Le scoreur choisit un archer dans le classement du tournoi et déclare **Abandon** (relégué
// en fin de classement) ou **Disqualification** (sorti du classement). L'acte est **réversible**
// (« Annuler ») tant que le tournoi n'est pas terminé (`D-15`). Le classement se resynchronise seul.

import { useState } from 'react'
import type { LigneClassement } from '../competition/api'
import { useClassement } from '../competition/hooks'
import { ChoixCreneau } from '../departs/ChoixCreneau'
import { useDeparts } from '../departs/hooks'
import { departDeSalle } from '../salle/rotation'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useAnnulerForfaitQualif, useDeclarerForfaitQualif } from './hooks'

export function PanneauForfaitsQualif({ tournoiId }: { tournoiId: number }) {
  // ⚠️ **Le classement est celui d'un créneau** (ADR-0075) : ce panneau listait « les archers du
  // tournoi », ce qui n'existe plus. Le défaut est le départ qu'on tire ; le sélecteur reste, parce
  // qu'un scoreur peut avoir à statuer sur un archer d'un **autre** créneau — le lui interdire
  // serait une régression déguisée en simplification.
  const [choixDepart, setChoixDepart] = useState<number | null>(null)
  const departs = useDeparts(tournoiId)
  const liste = departs.data ?? []
  const departId = choixDepart ?? departDeSalle(liste)?.id ?? null
  const classement = useClassement(tournoiId, departId)
  const declarer = useDeclarerForfaitQualif(tournoiId)
  const annuler = useAnnulerForfaitQualif(tournoiId)

  const lignes = classement.data?.lignes ?? []

  return (
    <section className="carte">
      <h3 className="carte__titre">Forfaits — qualification</h3>
      <p className="carte__etat">
        Déclarez l'abandon ou la disqualification d'un archer. Ses flèches déjà tirées sont
        conservées ; l'acte est réversible tant que le tournoi n'est pas terminé.
      </p>
      <ChoixCreneau departs={liste} valeur={departId} surChangement={setChoixDepart} />
      <MessageErreur erreur={declarer.error ?? annuler.error} />
      {lignes.length === 0 ? (
        <p className="carte__etat">Aucun archer inscrit pour l'instant.</p>
      ) : (
        <ul className="forfaits-liste">
          {lignes.map((ligne) => (
            <LigneForfait
              key={ligne.archer_id}
              ligne={ligne}
              enCours={declarer.isPending || annuler.isPending}
              onAbandon={() => declarer.mutate({ archerId: ligne.archer_id, nature: 'abandon' })}
              onDsq={() =>
                declarer.mutate({ archerId: ligne.archer_id, nature: 'disqualification' })
              }
              onAnnuler={() => annuler.mutate(ligne.archer_id)}
            />
          ))}
        </ul>
      )}
    </section>
  )
}

function LigneForfait({
  ligne,
  enCours,
  onAbandon,
  onDsq,
  onAnnuler,
}: {
  ligne: LigneClassement
  enCours: boolean
  onAbandon: () => void
  onDsq: () => void
  onAnnuler: () => void
}) {
  const identite = `${ligne.nom} ${ligne.prenom}`
  const forfait = ligne.statut !== 'en_lice'

  return (
    <li className="forfaits-liste__ligne">
      <span className="forfaits-liste__nom">
        {identite}
        {forfait && (
          <span className="table__badge-forfait">
            {' '}
            {ligne.statut === 'abandon' ? 'Abandon' : 'Disqualifié'}
          </span>
        )}
      </span>
      <span className="forfaits-liste__actions">
        {forfait ? (
          <button type="button" className="lien" disabled={enCours} onClick={onAnnuler}>
            Annuler
          </button>
        ) : (
          <>
            <button type="button" disabled={enCours} onClick={onAbandon}>
              Abandon
            </button>
            <button type="button" className="bouton--danger" disabled={enCours} onClick={onDsq}>
              Disqualifier
            </button>
          </>
        )}
      </span>
    </li>
  )
}
