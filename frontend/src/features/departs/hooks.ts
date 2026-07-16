// Hooks React Query de la feature « departs » (E02US004, ADR-0017).
//
// La liste des départs d'un tournoi est de l'état **serveur** (lecture) ; créer/éditer/supprimer
// sont des **mutations** qui invalident cette liste (rafraîchissement immédiat, en plus de la
// diffusion temps réel post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  creerDepart,
  getDeparts,
  type ModifierDepart,
  modifierDepart,
  type NouveauDepart,
  supprimerDepart,
} from './api'

const cleDeparts = (tournoiId: number) => ['departs', tournoiId] as const

export function useDeparts(tournoiId: number) {
  return useQuery({
    queryKey: cleDeparts(tournoiId),
    queryFn: () => getDeparts(tournoiId),
  })
}

export function useCreerDepart(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouveauDepart) => creerDepart(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleDeparts(tournoiId) }),
  })
}

export function useModifierDepart(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ departId, entree }: { departId: number; entree: ModifierDepart }) =>
      modifierDepart(tournoiId, departId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleDeparts(tournoiId) }),
  })
}

export function useSupprimerDepart(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (departId: number) => supprimerDepart(tournoiId, departId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleDeparts(tournoiId) }),
  })
}
