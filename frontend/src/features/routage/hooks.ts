// Hooks React Query du panneau de routage (E04US018).
//
// Le panneau est **live** : la cible d'un archer se fige au moment où l'organisateur lance le tour
// (`LiveEvent('tour_lance')`, E12US002), et son adversaire se révèle quand le duel amont est validé
// par un autre scoreur. Ces deux bascules viennent d'ailleurs que de l'écran courant — d'où le
// même poll court que le feu vert (E12US002) et la supervision (E12US001), et `staleTime: 0`
// (surcharge le staleTime global : c'est un écran vivant, pas une fiche).
//
// Attention : la clé de cache inclut la **liste d'archers**, pas seulement le tournoi. Sans elle,
// deux panneaux ouverts sur deux cibles se voleraient leur cache — le poste B afficherait les
// destinations du poste A.

import { useQuery } from '@tanstack/react-query'
import { getRoutage } from './api'

const INTERVALLE_POLL_MS = 5000

const cleRoutage = (tournoiId: number, archerIds: number[], phaseId: number | null) =>
  ['routage', tournoiId, phaseId, archerIds.join(',')] as const

export function useRoutage(
  tournoiId: number,
  archerIds: number[],
  phaseId: number | null = null,
  actif = true,
) {
  return useQuery({
    queryKey: cleRoutage(tournoiId, archerIds, phaseId),
    queryFn: () => getRoutage(tournoiId, archerIds, phaseId),
    // Panneau fermé ou aucun archer à router : pas de requête (et pas de poll en arrière-plan sur
    // un écran de saisie, où chaque round-trip compte le jour J).
    enabled: actif && archerIds.length > 0,
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}
