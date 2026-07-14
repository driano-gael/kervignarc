// Hooks React Query de la feature « barème de qualification » (E01US009).
//
// Le barème d'un tournoi est de l'état **serveur** (lecture) ; le définir est une **mutation** qui
// invalide cette lecture (rafraîchissement immédiat, en plus de la diffusion temps réel
// post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type DefinitionBareme, definirBareme, getBaremeDuTournoi } from './api'

const cleBareme = (tournoiId: number) => ['bareme-qualification', tournoiId] as const

export function useBaremeQualification(tournoiId: number) {
  return useQuery({
    queryKey: cleBareme(tournoiId),
    queryFn: () => getBaremeDuTournoi(tournoiId),
  })
}

export function useDefinirBareme(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: DefinitionBareme) => definirBareme(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleBareme(tournoiId) }),
  })
}
