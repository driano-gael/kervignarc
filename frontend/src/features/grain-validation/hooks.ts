// Hooks React Query de la feature « grain de validation » (E01US015).
//
// Le grain d'un tournoi est de l'état **serveur** (lecture) ; le définir est une **mutation** qui
// invalide cette lecture (rafraîchissement immédiat, en plus de la diffusion temps réel
// post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type DefinitionGrain, definirGrain, getGrainDuTournoi } from './api'

const cleGrain = (tournoiId: number) => ['grain-validation', tournoiId] as const

export function useGrainValidation(tournoiId: number) {
  return useQuery({
    queryKey: cleGrain(tournoiId),
    queryFn: () => getGrainDuTournoi(tournoiId),
  })
}

export function useDefinirGrain(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: DefinitionGrain) => definirGrain(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleGrain(tournoiId) }),
  })
}
