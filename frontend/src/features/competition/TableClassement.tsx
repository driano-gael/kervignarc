// Tableau de classement live (E00US011) : une ligne par archer (rang, cible, total). Les colonnes
// d'**action** (placer sur une cible, marquer une flèche) ne sont rendues que pour un **admin
// connecté** (E10US001) ; en consultation publique, le tableau est purement en lecture. Il se
// rafraîchit tout seul à chaque écriture (invalidation via le flux temps réel).

import { useState } from 'react'
import type { LigneClassement } from './api'
import { usePlacerArcher, useSaisirScore } from './hooks'

interface TableClassementProps {
  tournoiId: number
  lignes: LigneClassement[]
  admin: boolean
}

export function TableClassement({ tournoiId, lignes, admin }: TableClassementProps) {
  if (lignes.length === 0) {
    return <p className="carte__etat">Aucun archer inscrit pour l'instant.</p>
  }

  return (
    <table className="table">
      <thead>
        <tr>
          <th scope="col">Rang</th>
          <th scope="col">Archer</th>
          <th scope="col">Cible</th>
          <th scope="col">Total</th>
          {admin && <th scope="col">Placer</th>}
          {admin && <th scope="col">Marquer</th>}
        </tr>
      </thead>
      <tbody>
        {lignes.map((ligne) => (
          <LigneArcher key={ligne.archer_id} tournoiId={tournoiId} ligne={ligne} admin={admin} />
        ))}
      </tbody>
    </table>
  )
}

function LigneArcher({
  tournoiId,
  ligne,
  admin,
}: {
  tournoiId: number
  ligne: LigneClassement
  admin: boolean
}) {
  const [cible, setCible] = useState('')
  const [points, setPoints] = useState('')
  const placer = usePlacerArcher(tournoiId)
  const marquer = useSaisirScore(tournoiId)

  const soumettrePlacement = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    const valeur = Number(cible)
    if (!Number.isInteger(valeur) || valeur < 1) return
    placer.mutate({ archerId: ligne.archer_id, cible: valeur }, { onSuccess: () => setCible('') })
  }

  const soumettreScore = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    const valeur = Number(points)
    if (!Number.isInteger(valeur) || valeur < 0 || valeur > 10) return
    marquer.mutate(
      { archerId: ligne.archer_id, points: valeur },
      { onSuccess: () => setPoints('') },
    )
  }

  return (
    <tr>
      <td>{ligne.rang}</td>
      <td>{ligne.nom}</td>
      <td>{ligne.cible ?? '—'}</td>
      <td className="table__total">{ligne.total}</td>
      {admin && (
        <td>
          <form className="ligne-action" onSubmit={soumettrePlacement}>
            <input
              className="ligne-action__champ"
              type="number"
              min={1}
              value={cible}
              onChange={(e) => setCible(e.target.value)}
              aria-label={`Cible de ${ligne.nom}`}
            />
            <button type="submit" disabled={placer.isPending || cible === ''}>
              OK
            </button>
          </form>
        </td>
      )}
      {admin && (
        <td>
          <form className="ligne-action" onSubmit={soumettreScore}>
            <input
              className="ligne-action__champ"
              type="number"
              min={0}
              max={10}
              value={points}
              onChange={(e) => setPoints(e.target.value)}
              aria-label={`Flèche de ${ligne.nom} (0 à 10)`}
            />
            <button type="submit" disabled={marquer.isPending || points === ''}>
              +
            </button>
          </form>
        </td>
      )}
    </tr>
  )
}
