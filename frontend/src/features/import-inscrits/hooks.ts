import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apercuImport, confirmerImport } from './api'

export function useApercuImport(tournoiId: number) {
  return useMutation({ mutationFn: (fichier: File) => apercuImport(tournoiId, fichier) })
}

export function useConfirmerImport(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ fichier, homonymes }: { fichier: File; homonymes: number[] }) =>
      confirmerImport(tournoiId, fichier, homonymes),
    // Tout invalider plutôt qu'une liste de clés : l'import touche archers, clubs, inscriptions,
    // paiements, doublons et classement d'un coup — une liste oublierait la prochaine surface.
    onSuccess: () => queryClient.invalidateQueries(),
  })
}
