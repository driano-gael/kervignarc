// Hook React Query : santé du backend (fetch + cache), démontre le patron état-serveur.

import { useQuery } from '@tanstack/react-query'
import { getEtatBackend } from './api'

export function useEtatBackend() {
  return useQuery({ queryKey: ['sante-backend'], queryFn: getEtatBackend })
}
