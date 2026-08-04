// Hooks React Query de l'accueil-tableau de bord (E14US001).
//
// `useTransitions` lit les actions offertes par le statut courant (état serveur) ;
// `useTransitionnerTournoi` en applique une (mutation). Après une transition, le statut change :
// on invalide la **liste des tournois** (badge, frise, accueil contextualisé) **et** les
// transitions offertes (le nouveau statut en propose d'autres).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CLE_TOURNOIS } from '../competition/hooks'
import { getExigenceEffectif, getTransitions, transitionnerTournoi } from './api'

const cleTransitions = (tournoiId: number) => ['transitions', tournoiId] as const
const cleExigenceEffectif = (tournoiId: number) => ['exigence-effectif', tournoiId] as const

export function useTransitions(tournoiId: number) {
  return useQuery({
    queryKey: cleTransitions(tournoiId),
    queryFn: () => getTransitions(tournoiId),
  })
}

// E05US021 — l'effectif exigé par le déroulé, lu **en continu** pour prévenir avant le clic.
export function useExigenceEffectif(tournoiId: number) {
  return useQuery({
    queryKey: cleExigenceEffectif(tournoiId),
    queryFn: () => getExigenceEffectif(tournoiId),
  })
}

export function useTransitionnerTournoi(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (nom: string) => transitionnerTournoi(tournoiId, nom),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS })
      void queryClient.invalidateQueries({ queryKey: cleTransitions(tournoiId) })
      // Le minimum se déduit des **phases**, qu'une transition ne change pas ; mais les inscrits,
      // eux, bougent au fil de la journée et la frise est le seul endroit qui relit cet écran.
      void queryClient.invalidateQueries({ queryKey: cleExigenceEffectif(tournoiId) })
    },
  })
}
