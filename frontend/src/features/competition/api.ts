// Accès API de la feature « competition » (E00US011) : le fil rouge du walking skeleton —
// créer un tournoi, inscrire/placer un archer, saisir un score, lire le classement.
// Miroir des DTO exposés par `api/v1/competition.py` et `api/v1/tournois.py`.

import { fetchJson } from '../../shared/api/client'

export interface Tournoi {
  id: number
  nom: string
}

export interface Archer {
  id: number
  tournoi_id: number
  nom: string
  cible: number | null
}

export interface Score {
  id: number
  archer_id: number
  points: number
}

export interface LigneClassement {
  rang: number
  archer_id: number
  nom: string
  cible: number | null
  total: number
}

export interface Classement {
  tournoi_id: number
  lignes: LigneClassement[]
}

export function creerTournoi(nom: string): Promise<Tournoi> {
  return fetchJson<Tournoi>('/api/v1/tournois', {
    method: 'POST',
    body: JSON.stringify({ nom }),
  })
}

export function ajouterArcher(tournoiId: number, nom: string): Promise<Archer> {
  return fetchJson<Archer>(`/api/v1/tournois/${tournoiId}/archers`, {
    method: 'POST',
    body: JSON.stringify({ nom }),
  })
}

export function placerArcher(archerId: number, cible: number): Promise<Archer> {
  return fetchJson<Archer>(`/api/v1/archers/${archerId}/placement`, {
    method: 'POST',
    body: JSON.stringify({ cible }),
  })
}

export function saisirScore(archerId: number, points: number): Promise<Score> {
  return fetchJson<Score>(`/api/v1/archers/${archerId}/scores`, {
    method: 'POST',
    body: JSON.stringify({ points }),
  })
}

export function getClassement(tournoiId: number): Promise<Classement> {
  return fetchJson<Classement>(`/api/v1/tournois/${tournoiId}/classement`)
}
