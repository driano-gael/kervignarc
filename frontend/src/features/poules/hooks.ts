// Hooks React Query des **poules** (E05US023) — état serveur d'une phase de poules.
//
// Aucune mutation de tir ici : les rencontres s'écrivent par les hooks de `features/saisie-duels`
// avec la famille `'poule'` (ADR-0083 §7). C'est aussi pourquoi les **clés** de cache de l'état
// vivent là-bas : c'est l'écriture qui les invalide, et une clé écrite à deux endroits est une clé
// qui divergera — le projet a déjà payé ce défaut sur `clePhases`.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { clePoulesPubliques, clePoulesSaisie } from '../saisie-duels/hooks'
import {
  getEtatPoules,
  getEtatPoulesSaisie,
  regenererPlanPoules,
  type EtatPoules,
  type EtatPoulesSaisie,
} from './api'

/** L'état **en consultation** — contenu restreint, lecture ouverte. Écran d'organisation, salle. */
export function useEtatPoules(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: clePoulesPubliques(tournoiId, phaseId ?? 0),
    queryFn: () => getEtatPoules(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    // Même parti que le tableau : un refus déterministe (409 phase non réglée) ne gagne rien à être
    // réessayé, et un refetch au focus écraserait une frappe en cours.
    retry: false,
    refetchOnWindowFocus: false,
  })
}

/** L'état **de saisie** — le duel entier de chaque rencontre. Scoreur, dans son tournoi. */
export function useEtatPoulesSaisie(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: clePoulesSaisie(tournoiId, phaseId ?? 0),
    queryFn: () => getEtatPoulesSaisie(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    retry: false,
    refetchOnWindowFocus: false,
  })
}

/** Pose (ou repose) le plan de couloirs — **admin**. Le geste est grossier par construction : on
 * repose tout, parce que l'unité déplaçable est la poule et que la contiguïté de son bloc est
 * l'invariant du format.
 *
 * La réponse est la photo **publique** (c'est un écran d'organisation qui appelle), donc elle
 * alimente directement l'entrée de consultation. L'entrée de **saisie**, elle, est invalidée : une
 * repose change les blocs, donc les couloirs affichés au scoreur — la laisser telle quelle
 * afficherait les anciens couloirs jusqu'au prochain tir. */
export function useRegenererPlanPoules(tournoiId: number, phaseId: number) {
  const queryClient = useQueryClient()
  return useMutation<EtatPoules, Error, void>({
    mutationFn: () => regenererPlanPoules(tournoiId, phaseId),
    onSuccess: (etat) => {
      queryClient.setQueryData(clePoulesPubliques(tournoiId, phaseId), etat)
      void queryClient.invalidateQueries({ queryKey: clePoulesSaisie(tournoiId, phaseId) })
    },
  })
}

export type { EtatPoules, EtatPoulesSaisie }
