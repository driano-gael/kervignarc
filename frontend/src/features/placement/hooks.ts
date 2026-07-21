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
  type PlanDeCibles,
  deplacerInscription,
  getImpactRegeneration,
  getPlanDeCibles,
  placerRestants,
  regenererPlan,
} from './api'

// Exportée : la feature « suivi » (E07US006) rejoue ces plans via `useQueries` et doit partager
// EXACTEMENT la même clé, sinon le cache diverge (le plan public et le suivi refetcheraient chacun
// de leur côté au lieu de partager la donnée déjà chargée).
export const clePlan = (tournoiId: number, departId: number) =>
  ['plan-de-cibles', tournoiId, departId] as const

export function usePlanDeCibles(tournoiId: number, departId: number) {
  return useQuery({
    queryKey: clePlan(tournoiId, departId),
    queryFn: () => getPlanDeCibles(tournoiId, departId),
  })
}

// Clé de la prévisualisation d'impact (E12US007) : distincte du plan, pour l'invalider après une
// régénération (l'impact change) sans refetch inutile tant que le panneau de confirmation est fermé.
export const cleImpact = (tournoiId: number, departId: number) =>
  ['impact-regeneration', tournoiId, departId] as const

// N'interroge le serveur que lorsque `actif` (le panneau de confirmation est ouvert) : inutile de
// calculer l'impact tant que l'admin ne demande pas à régénérer.
export function useImpactRegeneration(tournoiId: number, departId: number, actif: boolean) {
  return useQuery({
    queryKey: cleImpact(tournoiId, departId),
    queryFn: () => getImpactRegeneration(tournoiId, departId),
    enabled: actif,
  })
}

export function useRegenerer(tournoiId: number, departId: number) {
  const queryClient = useQueryClient()
  // `confirme` (variable de mutation, typée explicitement) autorise l'écrasement d'un plan massif
  // (E12US007) ; les appelants passent `false` (première génération / plan sans score) ou `true`.
  return useMutation<PlanDeCibles, Error, boolean>({
    mutationFn: (confirme) => regenererPlan(tournoiId, departId, confirme),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: clePlan(tournoiId, departId) })
      queryClient.invalidateQueries({ queryKey: cleImpact(tournoiId, departId) })
    },
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
