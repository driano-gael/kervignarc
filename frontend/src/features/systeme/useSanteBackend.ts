// Hook React Query : santé du backend (fetch + cache), démontre le patron état-serveur.

import { useQuery } from '@tanstack/react-query'
import { getSanteBackend } from './api'

export function useSanteBackend() {
  return useQuery({ queryKey: ['sante-backend'], queryFn: getSanteBackend })
}
