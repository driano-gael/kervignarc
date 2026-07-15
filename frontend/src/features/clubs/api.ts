// Accès API de la feature « clubs » (E02US001) : CRUD du référentiel des clubs.
// Miroir des DTO exposés par `api/v1/clubs.py`.
//
// Routes **à la racine** (pas de `tournoiId`) : le référentiel est global, réutilisé d'une
// compétition à l'autre.

import { fetchJson } from '../../shared/api/client'

export interface Club {
  id: number
  nom: string
}

export interface NouveauClub {
  nom: string
}

// Le renommage porte sur le même champ que la création.
export type ModifierClub = NouveauClub

export function getClubs(): Promise<Club[]> {
  return fetchJson<Club[]>('/api/v1/clubs')
}

export function creerClub(entree: NouveauClub): Promise<Club> {
  return fetchJson<Club>('/api/v1/clubs', {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function modifierClub(id: number, entree: ModifierClub): Promise<Club> {
  return fetchJson<Club>(`/api/v1/clubs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function supprimerClub(id: number): Promise<void> {
  return fetchJson<void>(`/api/v1/clubs/${id}`, { method: 'DELETE' })
}
