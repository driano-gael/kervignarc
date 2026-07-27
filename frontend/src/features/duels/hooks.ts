// Hooks React Query de la feature « plan de duels » (E03US009, ADR-0048).
//
// Le plan de duels d'une phase est de l'état **serveur** (lecture) ; régénérer, déplacer et placer
// les restants sont des **mutations** qui invalident ce plan (rafraîchissement immédiat, en plus de
// la diffusion temps réel post-commit côté serveur). Le drag cible une **inscription** : le plan
// porte directement l'`inscription_id` de chaque duelliste (posé ou en réserve), aucune
// correspondance à reconstituer côté client.
//
// Jumeau de `placement/hooks.ts`, **sans** `useImpactRegeneration` : la régénération du plan de
// duels est directe (pas de confirmation chiffrée, ADR-0048).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  type Destination,
  type PlanDeDuels,
  deplacerDuelliste,
  getPlanDeDuels,
  placerRestantsDuels,
  regenererPlanDuels,
} from './api'

export const clePlanDuels = (tournoiId: number, phaseId: number) =>
  ['plan-de-duels', tournoiId, phaseId] as const

export function usePlanDeDuels(tournoiId: number, phaseId: number) {
  return useQuery({
    queryKey: clePlanDuels(tournoiId, phaseId),
    queryFn: () => getPlanDeDuels(tournoiId, phaseId),
  })
}

export function useRegenererDuels(tournoiId: number, phaseId: number) {
  const queryClient = useQueryClient()
  // Aucune variable de mutation : la régénération est directe (pas de `confirme`, ADR-0048).
  return useMutation<PlanDeDuels, Error, void>({
    mutationFn: () => regenererPlanDuels(tournoiId, phaseId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePlanDuels(tournoiId, phaseId) }),
  })
}

export function useDeplacerDuelliste(tournoiId: number, phaseId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      inscriptionId,
      destination,
    }: {
      inscriptionId: number
      destination: Destination
    }) => deplacerDuelliste(tournoiId, phaseId, inscriptionId, destination),
    // `onSettled` et non `onSuccess` : un 409 `deplacement_invalide` laisse l'état serveur
    // inchangé, mais on refetch quand même pour **réconcilier** l'affichage (le plan reste la
    // vérité serveur, jamais l'optimisme du drag).
    onSettled: () => queryClient.invalidateQueries({ queryKey: clePlanDuels(tournoiId, phaseId) }),
  })
}

export function usePlacerRestantsDuels(tournoiId: number, phaseId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => placerRestantsDuels(tournoiId, phaseId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePlanDuels(tournoiId, phaseId) }),
  })
}
