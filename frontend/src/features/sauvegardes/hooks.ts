import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getSauvegardes, restaurerSauvegarde, verifierSauvegarde } from './api'

const CLE_SAUVEGARDES = ['sauvegardes'] as const

export function useSauvegardes() {
  return useQuery({ queryKey: CLE_SAUVEGARDES, queryFn: getSauvegardes })
}

export function useVerifierSauvegarde() {
  return useMutation({ mutationFn: verifierSauvegarde })
}

export function useRestaurerSauvegarde() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: restaurerSauvegarde,
    // **Tout** le cache : la base entière a changé, tous tournois confondus. La diffusion
    // « données modifiées » le ferait aussi, mais pas avant que le WebSocket l'ait livrée.
    onSuccess: () => queryClient.invalidateQueries(),
  })
}
