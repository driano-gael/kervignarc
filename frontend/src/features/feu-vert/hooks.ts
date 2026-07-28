// Hooks React Query du pilotage d'un tour (E12US002, ADR-0056).
//
// Le feu vert est **live** : un duel devient prêt dès que sa source est validée par un scoreur, ou
// bloqué si le classement change. Un poll court (comme la supervision, E12US001) capte ces bascules
// — la diffusion WebSocket du lancement ne suffit pas, car ce sont les **validations de duels** (un
// autre flux) qui font avancer le tableau. `staleTime: 0` surcharge le staleTime global (écran live).
// Le lancement est une **mutation** qui ré-invalide feu vert + impact.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getFeuVert, getImpactLancement, lancerTour } from './api'

const INTERVALLE_POLL_MS = 5000

const cleFeuVert = (tournoiId: number, phaseId: number) => ['feu-vert', tournoiId, phaseId] as const
const cleImpact = (tournoiId: number, phaseId: number) =>
  ['impact-lancement', tournoiId, phaseId] as const

export function useFeuVert(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleFeuVert(tournoiId, phaseId ?? 0),
    queryFn: () => getFeuVert(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

export function useImpactLancement(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleImpact(tournoiId, phaseId ?? 0),
    queryFn: () => getImpactLancement(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

export function useLancerTour(tournoiId: number, phaseId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => lancerTour(tournoiId, phaseId as number),
    onSuccess: () => {
      if (phaseId === null) return
      queryClient.invalidateQueries({ queryKey: cleFeuVert(tournoiId, phaseId) })
      queryClient.invalidateQueries({ queryKey: cleImpact(tournoiId, phaseId) })
    },
  })
}
