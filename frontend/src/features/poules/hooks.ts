// Hooks React Query des **poules** (E05US023) — état serveur d'une phase de poules.
//
// Aucune mutation de tir ici : les rencontres s'écrivent par les hooks de `features/saisie-duels`
// avec la famille `'poule'` (ADR-0083 §7). C'est aussi pourquoi la **clé** de cache de l'état vit
// là-bas (`clePoules`) : c'est l'écriture qui l'invalide, et une clé écrite à deux endroits est une
// clé qui divergera — le projet a déjà payé ce défaut sur `clePhases`.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { clePoules } from '../saisie-duels/hooks'
import { getEtatPoules, regenererPlanPoules, type EtatPoules } from './api'

export function useEtatPoules(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: clePoules(tournoiId, phaseId ?? 0),
    queryFn: () => getEtatPoules(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    // Même parti que le tableau : un refus déterministe (409 phase non réglée) ne gagne rien à être
    // réessayé, et un refetch au focus écraserait une frappe en cours.
    retry: false,
    refetchOnWindowFocus: false,
  })
}

/** Pose (ou repose) le plan de couloirs — **admin**. Le geste est grossier par construction : on
 * repose tout, parce que l'unité déplaçable est la poule et que la contiguïté de son bloc est
 * l'invariant du format. */
export function useRegenererPlanPoules(tournoiId: number, phaseId: number) {
  const queryClient = useQueryClient()
  return useMutation<EtatPoules, Error, void>({
    mutationFn: () => regenererPlanPoules(tournoiId, phaseId),
    onSuccess: (etat) => {
      queryClient.setQueryData(clePoules(tournoiId, phaseId), etat)
    },
  })
}
