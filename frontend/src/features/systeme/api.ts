// Accès API de la feature « système » (E00US010) : sonde de santé du backend.

import { fetchJson } from '../../shared/api/client'

export interface EtatBackend {
  status: string
}

export function getEtatBackend(): Promise<EtatBackend> {
  return fetchJson<EtatBackend>('/health')
}
