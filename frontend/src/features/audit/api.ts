// Accès API de la feature « audit » (E16US016) : consultation du journal d'un tournoi.
// Miroir des DTO exposés par `api/v1/audit.py`. Lecture **admin** — un journal de litiges ne
// s'ouvre pas au public (ADR-0050).

import { fetchJson } from '../../shared/api/client'

export interface EntreeAudit {
  id: number
  tournoi_id: number
  // Slug stable de l'acte (`validation`, `correction_score`, …) : c'est la **valeur du domaine**,
  // pas un libellé. La traduction en clair est un choix d'IHM, elle vit dans `presentation.ts`.
  action: string
  auteur: string
  // Instant **UTC** en ISO-8601, tel que le serveur le stocke.
  horodatage: string
  objet: string
  avant: string | null
  apres: string | null
}

export function getAudit(tournoiId: number): Promise<EntreeAudit[]> {
  return fetchJson<EntreeAudit[]>(`/api/v1/tournois/${tournoiId}/audit`)
}
