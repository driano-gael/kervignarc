// Hooks React Query de la feature « grain de validation » (E01US015).
//
// Le grain d'un tournoi est de l'état **serveur** (lecture) ; le définir est une **mutation** qui
// invalide cette lecture (rafraîchissement immédiat, en plus de la diffusion temps réel
// post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cleQualifications } from '../bareme/hooks'
import { type DefinitionGrain, definirGrain, definirGrainEtape, getGrainDuTournoi } from './api'

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
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cleGrain(tournoiId) })
      void queryClient.invalidateQueries({ queryKey: cleQualifications(tournoiId) })
    },
  })
}

// --- E05US025 : réglages par qualification (ADR-0082) -------------------------------------------
//
// ⚠️ La clé de lecture vient de la feature « barème » (`cleQualifications`) : les deux écrans
// règlent **la même** liste de qualifications, et deux clés distinctes pour une seule ressource
// laisseraient l'un afficher un réglage que l'autre vient de changer.

export function useDefinirGrainEtape(tournoiId: number, etapeId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: DefinitionGrain) => definirGrainEtape(tournoiId, etapeId, entree),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cleQualifications(tournoiId) })
      void queryClient.invalidateQueries({ queryKey: cleGrain(tournoiId) })
    },
  })
}
