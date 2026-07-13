// Accès API de la feature « catégories » (E01US003) : CRUD des catégories d'un tournoi.
// Miroir des DTO exposés par `api/v1/categories.py`.

import { fetchJson } from '../../shared/api/client'

export type SexeCategorie = 'H' | 'F' | 'mixte'

export interface Categorie {
  id: number
  tournoi_id: number
  libelle: string
  arme: string | null
  tranche_age: string | null
  sexe: SexeCategorie | null
}

export interface NouvelleCategorie {
  libelle: string
  arme?: string | null
  tranche_age?: string | null
  sexe?: SexeCategorie | null
}

// L'édition porte sur les mêmes champs que la création.
export type ModifierCategorie = NouvelleCategorie

export function getCategories(tournoiId: number): Promise<Categorie[]> {
  return fetchJson<Categorie[]>(`/api/v1/tournois/${tournoiId}/categories`)
}

export function creerCategorie(tournoiId: number, entree: NouvelleCategorie): Promise<Categorie> {
  return fetchJson<Categorie>(`/api/v1/tournois/${tournoiId}/categories`, {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function modifierCategorie(id: number, entree: ModifierCategorie): Promise<Categorie> {
  return fetchJson<Categorie>(`/api/v1/categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function supprimerCategorie(id: number): Promise<void> {
  return fetchJson<void>(`/api/v1/categories/${id}`, { method: 'DELETE' })
}
