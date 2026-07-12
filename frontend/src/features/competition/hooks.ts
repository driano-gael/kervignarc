// Hooks React Query de la feature « competition » (E00US011).
//
// Le classement est l'état **serveur** (lecture) ; les autres cas d'usage sont des
// **mutations**. Après chaque écriture, le backend diffuse un événement WebSocket qui, via
// `useRealtime`, invalide le cache — le classement se met donc à jour **en direct** sur tous
// les clients. On invalide aussi côté mutation (onSuccess) pour un rafraîchissement immédiat
// même si le lien temps réel est momentanément coupé.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ajouterArcher, creerTournoi, getClassement, placerArcher, saisirScore } from './api'

const cleClassement = (tournoiId: number) => ['classement', tournoiId] as const

export function useClassement(tournoiId: number | null) {
  return useQuery({
    queryKey: ['classement', tournoiId],
    queryFn: () => getClassement(tournoiId as number),
    enabled: tournoiId !== null,
  })
}

export function useCreerTournoi() {
  return useMutation({ mutationFn: (nom: string) => creerTournoi(nom) })
}

export function useAjouterArcher(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (nom: string) => ajouterArcher(tournoiId, nom),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}

export function usePlacerArcher(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ archerId, cible }: { archerId: number; cible: number }) =>
      placerArcher(archerId, cible),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}

export function useSaisirScore(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ archerId, points }: { archerId: number; points: number }) =>
      saisirScore(archerId, points),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}
