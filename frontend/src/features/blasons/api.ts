// Accès API de la feature « blasons » (E01US005) : CRUD des blasons d'un tournoi.
// Miroir des DTO exposés par `api/v1/blasons.py`.

import { fetchJson } from '../../shared/api/client'

export interface Blason {
  id: number
  tournoi_id: number
  nom: string
  taille: number
  capacite: number
}

export interface NouveauBlason {
  nom: string
  taille: number
  capacite: number
}

// L'édition porte sur les mêmes champs que la création.
export type ModifierBlason = NouveauBlason

export function getBlasons(tournoiId: number): Promise<Blason[]> {
  return fetchJson<Blason[]>(`/api/v1/tournois/${tournoiId}/blasons`)
}

export function creerBlason(tournoiId: number, entree: NouveauBlason): Promise<Blason> {
  return fetchJson<Blason>(`/api/v1/tournois/${tournoiId}/blasons`, {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function modifierBlason(id: number, entree: ModifierBlason): Promise<Blason> {
  return fetchJson<Blason>(`/api/v1/blasons/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function supprimerBlason(id: number): Promise<void> {
  return fetchJson<void>(`/api/v1/blasons/${id}`, { method: 'DELETE' })
}
