// Hooks React Query de la feature « postes » (E04US001, volet **préparation** admin).
//
// La liste des codes de cible est de l'état **serveur** (lecture admin) ; la préparation est une
// **mutation** idempotente qui invalide cette liste (rafraîchissement immédiat).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getPostes, getQrCible, preparerPostes, telechargerEtiquettesQr } from './api'

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

// Le PDF des étiquettes (A12, 04/08/2026) : une **action**, pas de l'état serveur — `useMutation`,
// comme les téléchargements de la feature « exports ». Un `useQuery` déclencherait la génération au
// montage de l'écran et mettrait un PDF en cache, pour rien.
export function useTelechargerEtiquettesQr(tournoiId: number) {
  return useMutation({ mutationFn: () => telechargerEtiquettesQr(tournoiId) })
}

// QR de rattachement d'une cible (E11US008) : l'**image** (SVG) est de l'état **serveur**, mise en
// cache par React Query (règle 10). `getQrCible` renvoie une **data URL** autoporteuse (aucun
// objectURL à révoquer) : le composant `QrCible` l'affiche directement, sans cycle de vie local.
export function useQrCible(tournoiId: number, cibleIndex: number) {
  return useQuery({
    queryKey: ['qr-cible', tournoiId, cibleIndex] as const,
    queryFn: () => getQrCible(tournoiId, cibleIndex),
  })
}
