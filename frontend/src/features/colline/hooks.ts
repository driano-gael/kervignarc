// Hooks React Query de la **colline** (E05US027) — état serveur d'une phase de colline.
//
// Aucune mutation de tir ici : les défis s'écrivent par les hooks de `features/saisie-duels` avec
// la famille `'colline'` (ADR-0083 §7). C'est aussi pourquoi les **clés** de cache vivent là-bas :
// c'est l'écriture qui les invalide, et une clé écrite à deux endroits est une clé qui divergera —
// le projet a déjà payé ce défaut sur `clePhases`.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { cleCollinePublique, cleCollineSaisie } from '../saisie-duels/hooks'
import {
  getEtatColline,
  getEtatCollineSaisie,
  regenererPlanColline,
  type EtatCollinePublique,
  type EtatCollineSaisie,
} from './api'

/** L'état **rédigé** — contenu restreint, lecture ouverte. Écran d'organisation, salle, public. */
export function useEtatColline(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleCollinePublique(tournoiId, phaseId ?? 0),
    queryFn: () => getEtatColline(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    // Même parti que les poules et le suisse : un refus déterministe (409 phase non réglée) ne
    // gagne rien à être réessayé, et un refetch au focus écraserait une frappe en cours.
    retry: false,
    refetchOnWindowFocus: false,
  })
}

/** L'état **de saisie** — le duel entier de chaque défi. Scoreur, dans son tournoi. */
export function useEtatCollineSaisie(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleCollineSaisie(tournoiId, phaseId ?? 0),
    queryFn: () => getEtatCollineSaisie(tournoiId, phaseId as number),
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
export function useRegenererPlanColline(tournoiId: number, phaseId: number) {
  const queryClient = useQueryClient()
  return useMutation<EtatCollinePublique, Error, void>({
    mutationFn: () => regenererPlanColline(tournoiId, phaseId),
    onSuccess: (etat) => {
      queryClient.setQueryData(cleCollinePublique(tournoiId, phaseId), etat)
      void queryClient.invalidateQueries({ queryKey: cleCollineSaisie(tournoiId, phaseId) })
    },
  })
}

export type { EtatCollinePublique, EtatCollineSaisie }
