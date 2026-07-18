// Hooks React Query de la feature « scoreurs » (E10US003).
//
// La liste des scoreurs d'un tournoi est de l'état **serveur** (lecture admin) ; créer/renommer/
// supprimer sont des **mutations** qui invalident cette liste (rafraîchissement immédiat, en plus
// de la diffusion temps réel post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  creerScoreur,
  getScoreurs,
  modifierScoreur,
  type NouveauScoreur,
  supprimerScoreur,
} from './api'

const cleScoreurs = (tournoiId: number) => ['scoreurs', tournoiId] as const

export function useScoreurs(tournoiId: number) {
  return useQuery({
    queryKey: cleScoreurs(tournoiId),
    queryFn: () => getScoreurs(tournoiId),
  })
}

export function useCreerScoreur(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouveauScoreur) => creerScoreur(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleScoreurs(tournoiId) }),
  })
}

export function useModifierScoreur(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ scoreurId, entree }: { scoreurId: number; entree: NouveauScoreur }) =>
      modifierScoreur(tournoiId, scoreurId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleScoreurs(tournoiId) }),
  })
}

export function useSupprimerScoreur(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (scoreurId: number) => supprimerScoreur(tournoiId, scoreurId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleScoreurs(tournoiId) }),
  })
}
