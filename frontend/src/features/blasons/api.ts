// Accès API de la feature « blasons » (E01US005) : CRUD des blasons d'un tournoi.
// Miroir des DTO exposés par `api/v1/blasons.py`.

import { fetchJson } from '../../shared/api/client'

// Vocabulaire des zones de score en salle, du centre vers l'extérieur (référentiel FFTA §4.2).
// Miroir de l'énuméré `ZoneScore` du domaine ; sert aussi d'ordre d'affichage.
export const ZONES_CANONIQUES = ['10', '9', '8', '7', '6', '5', '4', '3', '2', '1', 'M'] as const

// Vocabulaire **fermé**, comme `TrancheAge` côté catégories : une valeur hors de cette liste est
// une erreur de compilation ici, et un 400 à la frontière serveur.
export type Zone = (typeof ZONES_CANONIQUES)[number]

export const ZONE_MANQUE: Zone = 'M'

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
