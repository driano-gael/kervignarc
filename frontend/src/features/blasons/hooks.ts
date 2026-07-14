// Hooks React Query de la feature « blasons » (E01US005).
//
// La liste des blasons d'un tournoi est de l'état **serveur** (lecture) ; créer/éditer/
// supprimer sont des **mutations** qui invalident cette liste (rafraîchissement immédiat, en
// plus de la diffusion temps réel post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  creerBlason,
  getBlasons,
  type ModifierBlason,
  modifierBlason,
  type NouveauBlason,
  supprimerBlason,
} from './api'

const cleBlasons = (tournoiId: number) => ['blasons', tournoiId] as const

export function useBlasons(tournoiId: number) {
  return useQuery({
    queryKey: cleBlasons(tournoiId),
    queryFn: () => getBlasons(tournoiId),
  })
}

export function useCreerBlason(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouveauBlason) => creerBlason(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleBlasons(tournoiId) }),
  })
}

export function useModifierBlason(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, entree }: { id: number; entree: ModifierBlason }) =>
      modifierBlason(id, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleBlasons(tournoiId) }),
  })
}

export function useSupprimerBlason(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => supprimerBlason(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleBlasons(tournoiId) }),
  })
}
