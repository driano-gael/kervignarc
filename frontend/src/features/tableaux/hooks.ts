// Hooks React Query de la vue publique des tableaux (E07US005).
//
// **Live** au sens du CA : le rafraîchissement principal est le canal temps réel — toute écriture
// serveur publie un `donnees_modifiees` post-commit que `useRealtime` traduit en invalidation
// globale, donc l'arbre se remet à jour tout seul dès qu'un scoreur valide un duel. Le poll n'est
// qu'un **filet** (WebSocket tombé, événement manqué), d'où un intervalle long.
//
// ⚠️ `# DETTE-031`, que cette US **élargit**. Chaque appel reconstruit intégralement chaque tableau
// du tournoi côté serveur (classement complet, arbre rebâti, duels rejoués), sans cache ni plafond,
// sur une route publique non authentifiée. Deux aggravations propres à cette US :
//  - la reconstruction est payée **une fois par phase en tableau**, pas une fois par appel ;
//  - la surface est en **autant d'exemplaires qu'il y a de spectateurs** — même régime que la carte
//    de suivi d'E07US008, et le cache React Query étant par navigateur, rien ne se mutualise.
// D'où `actif` : les appelants qui n'affichent pas cette vue ne montent pas la requête. C'est le
// même correctif qu'`EcranSalle` a dû appliquer à `useSuiviDeroule` (l'endpoint le plus cher du
// serveur, interrogé pendant les deux tiers du cycle où l'écran montrait autre chose).

import { useQuery } from '@tanstack/react-query'
import { getTableaux } from './api'

const INTERVALLE_POLL_MS = 20000

const cleTableaux = (tournoiId: number) => ['tableaux', tournoiId] as const

export function useTableaux(tournoiId: number, actif = true) {
  return useQuery({
    queryKey: cleTableaux(tournoiId),
    queryFn: () => getTableaux(tournoiId),
    enabled: actif,
    refetchInterval: INTERVALLE_POLL_MS,
    // Écran vivant, pas une fiche : ce qu'on relit doit être considéré périmé d'emblée.
    staleTime: 0,
  })
}
