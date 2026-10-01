// Hooks React Query de la feature « équipes » (E13US002). Chaque mutation invalide la liste.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ajouterMembre,
  creerEquipe,
  type EntreeEquipe,
  getEquipes,
  modifierEquipe,
  retirerMembre,
  supprimerEquipe,
} from './api'

export const cleEquipes = (tournoiId: number) => ['equipes', tournoiId] as const

export function useEquipes(tournoiId: number) {
  return useQuery({
    queryKey: cleEquipes(tournoiId),
    queryFn: () => getEquipes(tournoiId),
    // ⚠️ La conformité se lit sur la catégorie des membres, éditable depuis d'autres écrans
    // (CA 5) : à l'ouverture, on ne sert pas le cache de 30 s.
    refetchOnMount: 'always',
  })
}

function useInvaliderEquipes(tournoiId: number) {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: cleEquipes(tournoiId) })
}

export function useCreerEquipe(tournoiId: number) {
  const invalider = useInvaliderEquipes(tournoiId)
  return useMutation({
    mutationFn: (entree: EntreeEquipe) => creerEquipe(tournoiId, entree),
    onSuccess: invalider,
  })
}

export function useModifierEquipe(tournoiId: number) {
  const invalider = useInvaliderEquipes(tournoiId)
  return useMutation({
    mutationFn: ({ equipeId, entree }: { equipeId: number; entree: EntreeEquipe }) =>
      modifierEquipe(tournoiId, equipeId, entree),
    onSuccess: invalider,
  })
}

export function useSupprimerEquipe(tournoiId: number) {
  const invalider = useInvaliderEquipes(tournoiId)
  return useMutation({
    mutationFn: (equipeId: number) => supprimerEquipe(tournoiId, equipeId),
    onSuccess: invalider,
  })
}

export function useAjouterMembre(tournoiId: number) {
  const invalider = useInvaliderEquipes(tournoiId)
  return useMutation({
    mutationFn: ({ equipeId, archerId }: { equipeId: number; archerId: number }) =>
      ajouterMembre(tournoiId, equipeId, archerId),
    onSuccess: invalider,
  })
}

export function useRetirerMembre(tournoiId: number) {
  const invalider = useInvaliderEquipes(tournoiId)
  return useMutation({
    mutationFn: ({ equipeId, archerId }: { equipeId: number; archerId: number }) =>
      retirerMembre(tournoiId, equipeId, archerId),
    onSuccess: invalider,
  })
}
