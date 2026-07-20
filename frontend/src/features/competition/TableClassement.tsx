// Tableau du classement de qualification (E06US001). Une ligne par archer : rang **de catégorie** et
// rang **scratch** (global), identité, catégorie, cible, total, et le décompte de **10** et de **9**
// qui rend le départage FFTA lisible (à total égal, plus de 10 puis de 9 — `referentiel-ffta` §8.1).
// Il se rafraîchit tout seul à chaque saisie (invalidation via le flux temps réel).
//
// Surface de **lecture** : le classement sert à connaître les positions. Le placement inline reste
// offert à l'admin (colonne « Placer ») ; la saisie des scores, elle, se fait sur l'écran de saisie
// dédié (E04US002) — l'ancien bouton « Marquer » du walking skeleton écrivait un score que le
// classement ne lit plus (il dérive des séries de saisie), il a donc été retiré.
//
// Le club encore inconnu y est signalé (E02US002, ADR-0014) : le classement est la surface qu'on
// regarde toute la journée, c'est là que l'anomalie se remarque ; l'écran d'admin la répare.

import { useState } from 'react'
import type { LigneClassement } from './api'
import { usePlacerArcher } from './hooks'

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
          <th scope="col">Rang cat.</th>
          <th scope="col">Scratch</th>
          <th scope="col">Archer</th>
          <th scope="col">Catégorie</th>
          <th scope="col">Cible</th>
          <th scope="col">Total</th>
          <th scope="col" title="Nombre de 10 (départage FFTA)">
            10
          </th>
          <th scope="col" title="Nombre de 9 (départage FFTA)">
            9
          </th>
          {admin && <th scope="col">Placer</th>}
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
  const placer = usePlacerArcher(tournoiId)

  const soumettrePlacement = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    const valeur = Number(cible)
    if (!Number.isInteger(valeur) || valeur < 1) return
    placer.mutate({ archerId: ligne.archer_id, cible: valeur }, { onSuccess: () => setCible('') })
  }

  // Nom **et** prénom : depuis E02US002, deux homonymes confirmés (un père et son fils) peuvent
  // coexister — les distinguer à l'écran est le minimum vital.
  const identite = `${ligne.nom} ${ligne.prenom}`

  return (
    <tr>
      <td>{ligne.rang_categorie}</td>
      <td className="table__scratch">{ligne.rang_scratch}</td>
      <td>
        {identite}
        {ligne.club_id === null && (
          <span
            className="table__anomalie"
            title="Renseignez son club pour compléter l'inscription"
          >
            {' '}
            Club inconnu
          </span>
        )}
      </td>
      <td>{ligne.categorie_libelle}</td>
      <td>{ligne.cible ?? '—'}</td>
      <td className="table__total">{ligne.total}</td>
      <td>{ligne.nb_dix}</td>
      <td>{ligne.nb_neuf}</td>
      {admin && (
        <td>
          <form className="ligne-action" onSubmit={soumettrePlacement}>
            <input
              className="ligne-action__champ"
              type="number"
              min={1}
              value={cible}
              onChange={(e) => setCible(e.target.value)}
              aria-label={`Cible de ${identite}`}
            />
            <button type="submit" disabled={placer.isPending || cible === ''}>
              OK
            </button>
          </form>
        </td>
      )}
    </tr>
  )
}
