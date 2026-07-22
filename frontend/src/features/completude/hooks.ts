// Hooks React Query de la complétude du tournoi (E12US005).
//
// Lecture **live** par poll court, comme la supervision (E12US001) : la complétude bouge au fil des
// validations de séries et des marquages de paiement, qui n'émettent pas tous un événement dédié — le
// `refetchInterval` capte l'avancement sans dépendre d'une diffusion. `staleTime: 0` surcharge le
// `staleTime` global (30 s, inadapté à un écran de suivi). Le passage à *terminé* réutilise la
// mutation de `competition` (une seule voie d'écriture du cycle de vie) et ré-invalide la complétude.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { terminerTournoi } from '../competition/api'
import { getCompletude } from './api'

const INTERVALLE_POLL_MS = 5000

const cleCompletude = (tournoiId: number) => ['completude', tournoiId] as const

export function useCompletude(tournoiId: number) {
  return useQuery({
    queryKey: cleCompletude(tournoiId),
    queryFn: () => getCompletude(tournoiId),
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

export function useTerminerDepuisCompletude(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => terminerTournoi(tournoiId),
    onSuccess: () => {
      // La liste des tournois (statut → badge, accueil contextualisé) **et** la complétude (le
      // bouton disparaît, l'écran reflète l'état figé) se resynchronisent.
      queryClient.invalidateQueries({ queryKey: ['tournois'] })
      queryClient.invalidateQueries({ queryKey: cleCompletude(tournoiId) })
    },
  })
}
