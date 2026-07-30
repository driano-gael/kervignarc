// Hooks React Query de la feature « catégories » (E01US003).
//
// La liste des catégories d'un tournoi est de l'état **serveur** (lecture) ; créer/éditer/
// supprimer sont des **mutations** qui invalident cette liste (rafraîchissement immédiat, en
// plus de la diffusion temps réel post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  creerCategorie,
  getCategories,
  type ModifierCategorie,
  modifierCategorie,
  type NouvelleCategorie,
  supprimerCategorie,
} from './api'

const cleCategories = (tournoiId: number) => ['categories', tournoiId] as const

export function useCategories(tournoiId: number) {
  return useQuery({
    queryKey: cleCategories(tournoiId),
    queryFn: () => getCategories(tournoiId),
  })
}

export function useCreerCategorie(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouvelleCategorie) => creerCategorie(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleCategories(tournoiId) }),
  })
}

export function useModifierCategorie(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, entree }: { id: number; entree: ModifierCategorie }) =>
      modifierCategorie(id, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleCategories(tournoiId) }),
  })
}

export function useSupprimerCategorie(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => supprimerCategorie(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleCategories(tournoiId) }),
  })
}
