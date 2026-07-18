// Hooks React Query de la feature « placement » (E03US004, ADR-0024).
//
// Le plan de cibles d'un départ est de l'état **serveur** (lecture) ; régénérer, déplacer et placer
// les restants sont des **mutations** qui invalident ce plan (rafraîchissement immédiat, en plus de
// la diffusion temps réel post-commit côté serveur, qui invalide tout le cache). Le drag cible une
// **inscription** : le plan porte directement l'`inscription_id` de chaque archer (posé ou en
// réserve), aucune correspondance à reconstituer côté client.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  type Destination,
  deplacerInscription,
  getPlanDeCibles,
  placerRestants,
  regenererPlan,
} from './api'

const clePlan = (tournoiId: number, departId: number) =>
  ['plan-de-cibles', tournoiId, departId] as const

export function usePlanDeCibles(tournoiId: number, departId: number) {
  return useQuery({
    queryKey: clePlan(tournoiId, departId),
    queryFn: () => getPlanDeCibles(tournoiId, departId),
  })
}

export function useRegenerer(tournoiId: number, departId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => regenererPlan(tournoiId, departId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePlan(tournoiId, departId) }),
  })
}

export function useDeplacer(tournoiId: number, departId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      inscriptionId,
      destination,
    }: {
      inscriptionId: number
      destination: Destination
    }) => deplacerInscription(tournoiId, departId, inscriptionId, destination),
    // `onSettled` et non `onSuccess` : un 409 `deplacement_invalide` laisse l'état serveur
    // inchangé, mais on refetch quand même pour **réconcilier** l'affichage (le plan reste la
    // vérité serveur, jamais l'optimisme du drag).
    onSettled: () => queryClient.invalidateQueries({ queryKey: clePlan(tournoiId, departId) }),
  })
}

export function usePlacerRestants(tournoiId: number, departId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => placerRestants(tournoiId, departId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePlan(tournoiId, departId) }),
  })
}
