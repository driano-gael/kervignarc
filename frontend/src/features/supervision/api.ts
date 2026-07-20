// Accès API de la console de supervision (E12US001, ADR-0038). Miroir des DTO de
// `api/v1/supervision.py`. Console et révocation sont des routes **admin** (portée `'admin'` par
// défaut de `fetchJson`, en-tête `Authorization: Bearer`).

import { fetchJson } from '../../shared/api/client'
import type { EtatPoste } from './etat'

export interface Avancement {
  volee_courante: number
  nb_volees: number
}

export interface PosteSupervision {
  poste_id: number
  cible_index: number
  etat: EtatPoste
  derniere_saisie: string | null // ISO UTC, ou null si rien saisi
  ip: string | null // diagnostic (D-06), null si non rattaché
  avancement: Avancement | null // null si non rattaché ou sans départ courant
}

export interface Supervision {
  postes: PosteSupervision[]
  nb_en_ligne: number
  nb_total: number
}

export function getSupervision(tournoiId: number): Promise<Supervision> {
  return fetchJson<Supervision>(`/api/v1/tournois/${tournoiId}/supervision`)
}

export function revoquerPoste(tournoiId: number, posteId: number): Promise<void> {
  // 204 attendu (fetchJson renvoie undefined) : ferme les sessions du poste et oublie sa présence.
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/postes/${posteId}/revocation`, {
    method: 'POST',
  })
}
