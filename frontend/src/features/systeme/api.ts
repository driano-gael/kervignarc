// Accès API de la feature « système » (E00US010) : sonde de santé du backend.

import { fetchJson } from '../../shared/api/client'

export interface SanteBackend {
  status: string
}

export function getSanteBackend(): Promise<SanteBackend> {
  return fetchJson<SanteBackend>('/health')
}
