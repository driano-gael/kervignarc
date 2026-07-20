// Hooks React Query de la console de supervision (E12US001, ADR-0038).
//
// La console **poll** (rafraîchissement court) : le passage *hors ligne* d'un poste naît du **temps
// qui passe** sans heartbeat, pas d'un événement serveur — aucune diffusion WebSocket ne peut donc le
// signaler (ADR-0038 §4). Le `refetchInterval` capte à la fois les retours en ligne, les bascules
// hors ligne (expiration du seuil) et l'avancement. `staleTime: 0` surcharge le `staleTime` global de
// 30 s (inadapté à un écran live). La révocation est une **mutation** qui ré-invalide la console.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getSupervision, revoquerPoste } from './api'

const INTERVALLE_POLL_MS = 3000

const cleSupervision = (tournoiId: number) => ['supervision', tournoiId] as const

export function useSupervision(tournoiId: number) {
  return useQuery({
    queryKey: cleSupervision(tournoiId),
    queryFn: () => getSupervision(tournoiId),
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

export function useRevoquerPoste(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (posteId: number) => revoquerPoste(tournoiId, posteId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleSupervision(tournoiId) }),
  })
}
