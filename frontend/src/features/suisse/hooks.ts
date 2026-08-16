// Hooks React Query du **système suisse** (E05US030) — état serveur d'une phase de suisse.
//
// Aucune mutation de tir ici : les rencontres s'écrivent par les hooks de `features/saisie-duels`
// avec la famille `'suisse'` (ADR-0083 §7). C'est aussi pourquoi les **clés** de cache vivent
// là-bas : c'est l'écriture qui les invalide, et une clé écrite à deux endroits est une clé qui
// divergera — le projet a déjà payé ce défaut sur `clePhases`.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { cleSuissePublique, cleSuisseSaisie } from '../saisie-duels/hooks'
import {
  getEtatSuisse,
  getEtatSuisseSaisie,
  regenererPlanSuisse,
  type EtatSuissePublique,
  type EtatSuisseSaisie,
} from './api'

/** L'état **rédigé** — contenu restreint, lecture ouverte. Écran d'organisation, salle. */
export function useEtatSuisse(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleSuissePublique(tournoiId, phaseId ?? 0),
    queryFn: () => getEtatSuisse(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    // Même parti que les poules : un refus déterministe (409 phase non réglée) ne gagne rien à être
    // réessayé, et un refetch au focus écraserait une frappe en cours.
    retry: false,
    refetchOnWindowFocus: false,
  })
}

/** L'état **de saisie** — le duel entier de chaque rencontre. Scoreur, dans son tournoi. */
export function useEtatSuisseSaisie(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleSuisseSaisie(tournoiId, phaseId ?? 0),
    queryFn: () => getEtatSuisseSaisie(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    retry: false,
    refetchOnWindowFocus: false,
  })
}

/** Pose (ou repose) le plan de couloirs — **admin**.
 *
 * La réponse est la photo **rédigée** (c'est un écran d'organisation qui appelle), donc elle
 * alimente directement l'entrée de consultation. L'entrée de **saisie** est invalidée : une repose
 * change le bloc, donc les couloirs affichés au scoreur — la laisser telle quelle lui montrerait
 * les anciens jusqu'au prochain tir. */
export function useRegenererPlanSuisse(tournoiId: number, phaseId: number) {
  const queryClient = useQueryClient()
  return useMutation<EtatSuissePublique, Error, void>({
    mutationFn: () => regenererPlanSuisse(tournoiId, phaseId),
    onSuccess: (etat) => {
      queryClient.setQueryData(cleSuissePublique(tournoiId, phaseId), etat)
      void queryClient.invalidateQueries({ queryKey: cleSuisseSaisie(tournoiId, phaseId) })
    },
  })
}

export type { EtatSuissePublique, EtatSuisseSaisie }
