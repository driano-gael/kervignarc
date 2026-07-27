// Hooks React Query de la feature « postes » (E04US001, volet **préparation** admin).
//
// La liste des codes de cible est de l'état **serveur** (lecture admin) ; la préparation est une
// **mutation** idempotente qui invalide cette liste (rafraîchissement immédiat).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getPostes, getQrCible, preparerPostes } from './api'

const clePostes = (tournoiId: number) => ['postes', tournoiId] as const

export function usePostes(tournoiId: number) {
  return useQuery({
    queryKey: clePostes(tournoiId),
    queryFn: () => getPostes(tournoiId),
  })
}

export function usePreparerPostes(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => preparerPostes(tournoiId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePostes(tournoiId) }),
  })
}

// QR de rattachement d'une cible (E11US008) : l'**image** (blob SVG) est de l'état **serveur**, donc
// mise en cache par React Query (règle 10). Le composant `QrCible` en dérive un `objectURL` — au
// cycle de vie **local** (à révoquer), ce que le cache de React Query ne gère pas — dans son effet.
export function useQrCible(tournoiId: number, cibleIndex: number) {
  return useQuery({
    queryKey: ['qr-cible', tournoiId, cibleIndex] as const,
    queryFn: () => getQrCible(tournoiId, cibleIndex),
  })
}
