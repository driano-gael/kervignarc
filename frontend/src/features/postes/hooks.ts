// Hooks React Query de la feature « postes » (E04US001, volet **préparation** admin).
//
// La liste des codes de cible est de l'état **serveur** (lecture admin) ; la préparation est une
// **mutation** idempotente qui invalide cette liste (rafraîchissement immédiat).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getPostes, preparerPostes } from './api'

const clePostes = (tournoiId: number) => ['postes', tournoiId] as const

export function usePostes(tournoiId: number) {
  return useQuery({
    queryKey: clePostes(tournoiId),
    queryFn: () => getPostes(tournoiId),
  })
}

export function usePreparerPostes(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => preparerPostes(tournoiId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePostes(tournoiId) }),
  })
}
