// Hooks React Query de l'accueil-tableau de bord (E14US001).
//
// `useTransitions` lit les actions offertes par le statut courant (état serveur) ;
// `useTransitionnerTournoi` en applique une (mutation). Après une transition, le statut change :
// on invalide la **liste des tournois** (badge, frise, accueil contextualisé) **et** les
// transitions offertes (le nouveau statut en propose d'autres).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CLE_TOURNOIS } from '../competition/hooks'
import { getTransitions, transitionnerTournoi } from './api'

const cleTransitions = (tournoiId: number) => ['transitions', tournoiId] as const

export function useTransitions(tournoiId: number) {
  return useQuery({
    queryKey: cleTransitions(tournoiId),
    queryFn: () => getTransitions(tournoiId),
  })
}

export function useTransitionnerTournoi(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (nom: string) => transitionnerTournoi(tournoiId, nom),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS })
      void queryClient.invalidateQueries({ queryKey: cleTransitions(tournoiId) })
    },
  })
}
