// Accès API de la feature « blasons » (E01US005) : CRUD des blasons d'un tournoi.
// Miroir des DTO exposés par `api/v1/blasons.py`.

import { fetchJson } from '../../shared/api/client'
import type { Zone } from './zones'

// Le vocabulaire des zones vit dans `zones.ts` (module pur) ; réexporté ici par commodité.
export { ZONE_MANQUE, ZONES_CANONIQUES, type Zone } from './zones'

export interface Blason {
  id: number
  tournoi_id: number
  nom: string
  taille: number
  capacite: number
  // Valeurs de score admises (E01US014) : un triple 40 n'a pas les zones 5 → 1 (§4.4).
  zones: Zone[]
}

export interface NouveauBlason {
  nom: string
  taille: number
  capacite: number
  zones: Zone[]
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
