// « Où tire cet archer ? » — une ligne par créneau où il est posé (E12US006, `D-09`).
//
// ⚠️ **Remonté ici par E16US010, sur preuve** : deuxième consommateur réel (la recherche de la
// sidebar, puis la fiche d'archer du pilotage), jamais sur pari — c'est la règle du projet. Il vit
// dans `placement/` parce que c'est le plan de cibles qui fait autorité sur la place (ADR-0033),
// et parce que la recherche en dépendait déjà : le remonter n'ajoute qu'une arête.

import { useQueries } from '@tanstack/react-query'
import { useDeparts } from '../departs/hooks'
import { construireJournee } from '../suivi/suivi'
import { getPlanDeCibles, type PlanDeCibles } from './api'
import { clePlan } from './hooks'

// Ce qu'on CONNAÎT d'abord, puis erreur, puis chargement, et « pas encore placé » — le fait
// négatif — toujours en dernier, jamais à la place d'un plan qui charge ou qui échoue.
export function PlaceDeLArcher({ archerId, tournoiId }: { archerId: number; tournoiId: number }) {
  const departsQuery = useDeparts(tournoiId, true)
  const departs = departsQuery.data ?? []

  const plansResults = useQueries({
    queries: departs.map((d) => ({
      queryKey: clePlan(tournoiId, d.id),
      queryFn: () => getPlanDeCibles(tournoiId, d.id),
    })),
  })
  const plansParDepart = new Map<number, PlanDeCibles>()
  departs.forEach((d, i) => {
    const data = plansResults[i]?.data
    if (data) plansParDepart.set(d.id, data)
  })

  const journee = construireJournee(archerId, departs, plansParDepart)
  if (journee.length > 0) {
    return (
      <ul className="recherche-places">
        {journee.map((l) => (
          <li key={l.departId} className="recherche-place">
            Départ {l.numeroDepart}
            {l.horaire ? ` · ${l.horaire}` : ''} — Cible {l.cible} · couloir {l.position}
          </li>
        ))}
      </ul>
    )
  }
  if (departsQuery.isError || plansResults.some((r) => r.isError))
    return (
      <span className="recherche-place recherche-place--attente">
        Placement momentanément indisponible.
      </span>
    )
  if (departsQuery.isLoading || plansResults.some((r) => r.isLoading))
    return <span className="recherche-place recherche-place--attente">Chargement…</span>
  return <span className="recherche-place recherche-place--vide">Pas encore placé.</span>
}
