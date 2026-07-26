// Hooks React Query de la feature « exports » (E09US003).
//
// Un téléchargement n'est pas de l'état serveur à mettre en cache : c'est une **action** ponctuelle
// → `useMutation` (pas `useQuery`, qui déclencherait un fetch automatique et mettrait le PDF en
// cache). `isPending` désactive le bouton pendant la génération ; `error` alimente `MessageErreur`.

import { useMutation } from '@tanstack/react-query'
import { type OptionsPlacement, telechargerClubPaiement, telechargerPlacement } from './api'

export function useTelechargerPlacement(tournoiId: number) {
  return useMutation({
    mutationFn: (options: OptionsPlacement) => telechargerPlacement(tournoiId, options),
  })
}

export function useTelechargerClubPaiement(tournoiId: number) {
  return useMutation({
    mutationFn: () => telechargerClubPaiement(tournoiId),
  })
}
