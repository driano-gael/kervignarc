// Hooks React Query de la feature « barème de qualification » (E01US009).
//
// Le barème d'un tournoi est de l'état **serveur** (lecture) ; le définir est une **mutation** qui
// invalide cette lecture (rafraîchissement immédiat, en plus de la diffusion temps réel
// post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  type DefinitionBareme,
  definirBareme,
  definirBaremeEtape,
  getBaremeDuTournoi,
  getQualifications,
} from './api'

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

// --- E05US025 : réglages par qualification (ADR-0082) -------------------------------------------

const cleQualifications = (tournoiId: number) => ['qualifications', tournoiId] as const

export function useQualifications(tournoiId: number) {
  return useQuery({
    queryKey: cleQualifications(tournoiId),
    queryFn: () => getQualifications(tournoiId),
  })
}

export function useDefinirBaremeEtape(tournoiId: number, etapeId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: DefinitionBareme) => definirBaremeEtape(tournoiId, etapeId, entree),
    // Les deux lectures sont invalidées : la liste (qui porte les réglages affichés) **et** le
    // barème « du tournoi », que d'autres écrans lisent encore pour la première qualification.
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cleQualifications(tournoiId) })
      void queryClient.invalidateQueries({ queryKey: cleBareme(tournoiId) })
    },
  })
}
