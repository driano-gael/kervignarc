// Hooks React Query de la feature « inscriptions » (E02US009, ADR-0017).
//
// Les inscriptions d'un archer sont de l'état **serveur** (lecture) ; inscrire / marquer payé /
// désinscrire sont des **mutations** qui invalident cette liste (rafraîchissement immédiat, en plus
// de la diffusion temps réel post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { desinscrire, getInscriptions, inscrire, marquerPaye } from './api'

const cleInscriptions = (archerId: number) => ['inscriptions', archerId] as const

export function useInscriptions(archerId: number) {
  return useQuery({
    queryKey: cleInscriptions(archerId),
    queryFn: () => getInscriptions(archerId),
  })
}

export function useInscrire(archerId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (departId: number) => inscrire(archerId, departId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleInscriptions(archerId) }),
  })
}

export function useMarquerPaye(archerId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ inscriptionId, paye }: { inscriptionId: number; paye: boolean }) =>
      marquerPaye(inscriptionId, paye),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleInscriptions(archerId) }),
  })
}

export function useDesinscrire(archerId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (inscriptionId: number) => desinscrire(inscriptionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleInscriptions(archerId) }),
  })
}
