// Instance unique de React Query pour l'app (E00US010).
// Les mises à jour temps réel invalident le cache (voir `useRealtime`), d'où un
// `staleTime` non nul pour éviter les refetch redondants au montage.

import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})
