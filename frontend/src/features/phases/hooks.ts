// Hooks React Query de la feature « séquence de phases » (E05US001).
//
// La liste des phases d'un tournoi est de l'état **serveur** ; ajouter/éditer/réordonner/supprimer
// et les transitions de statut sont des **mutations** qui invalident cette liste. Le
// réordonnancement resynchronise en `onSettled` (succès **comme** échec 409) : on ne laisse jamais
// l'ordre optimiste du geste diverger de la vérité serveur (cf. `placement/hooks.ts`).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ajouterPhase,
  changerStatutPhase,
  type ConfigPhase,
  getPhases,
  modifierPhase,
  reordonnerPhases,
  supprimerPhase,
  type TransitionPhase,
} from './api'

const clePhases = (tournoiId: number) => ['phases', tournoiId] as const

export function usePhases(tournoiId: number) {
  return useQuery({
    queryKey: clePhases(tournoiId),
    queryFn: () => getPhases(tournoiId),
  })
}

export function useAjouterPhase(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (config: ConfigPhase) => ajouterPhase(tournoiId, config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePhases(tournoiId) }),
  })
}

export function useModifierPhase(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ phaseId, config }: { phaseId: number; config: ConfigPhase }) =>
      modifierPhase(tournoiId, phaseId, config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePhases(tournoiId) }),
  })
}

export function useReordonnerPhases(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (phases: number[]) => reordonnerPhases(tournoiId, phases),
    // Resync même en cas de refus serveur (422/409) : l'ordre affiché reste la vérité serveur.
    onSettled: () => queryClient.invalidateQueries({ queryKey: clePhases(tournoiId) }),
  })
}

export function useSupprimerPhase(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (phaseId: number) => supprimerPhase(tournoiId, phaseId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePhases(tournoiId) }),
  })
}

export function useChangerStatutPhase(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ phaseId, transition }: { phaseId: number; transition: TransitionPhase }) =>
      changerStatutPhase(tournoiId, phaseId, transition),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePhases(tournoiId) }),
  })
}
