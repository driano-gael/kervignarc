// Accès API de la feature « competition » (E00US011) : le fil rouge du walking skeleton —
// créer un tournoi, inscrire/placer un archer, saisir un score, lire le classement.
// Miroir des DTO exposés par `api/v1/competition.py` et `api/v1/tournois.py`.

import { fetchJson } from '../../shared/api/client'

export type TypeTournoi = 'officiel' | 'non_officiel'

// Cycle de vie d'un tournoi (E01US002) : brouillon → en cours → terminé.
export type StatutTournoi = 'brouillon' | 'en_cours' | 'termine'

export interface Tournoi {
  id: number
  nom: string
  date: string // ISO (AAAA-MM-JJ)
  lieu: string | null
  type_tournoi: TypeTournoi
  statut: StatutTournoi
  // Le tarif n'est plus au tournoi : il vit sur chaque départ (créneau), feature « departs »
  // (E02US004, ADR-0017).
}

export interface NouveauTournoi {
  nom: string
  date: string
  lieu?: string | null
  type_tournoi?: TypeTournoi
}

// L'édition porte sur les métadonnées uniquement ; le statut évolue via démarrer/terminer.
export type ModifierTournoi = NouveauTournoi

export interface Archer {
  id: number
  tournoi_id: number
  nom: string
  prenom: string
  categorie_id: number
  cible: number | null
  club_id: number | null
}

// Inscription d'un archer (E02US002). `categorie_id` est **obligatoire** ; `club_id` reste
// facultatif : `null` = club encore **inconnu**, jamais « aucun club » — en FFTA tout licencié en
// a un (ADR-0014). L'archer s'inscrit quand même, et l'écran signale l'anomalie à compléter.
export interface NouvelArcher {
  nom: string
  prenom: string
  categorie_id: number
  club_id: number | null
  // Confirmation de l'admin après un refus `homonyme_archer` (409) : déclare que ce nouvel
  // archer, malgré des nom/prénom/club identiques à un inscrit, est bien une autre personne.
  autoriser_homonyme?: boolean
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
  prenom: string
  cible: number | null
  // `null` = club encore **inconnu** (ADR-0014) : l'écran le signale pour qu'il soit complété.
  club_id: number | null
  total: number
}

export interface Classement {
  tournoi_id: number
  lignes: LigneClassement[]
}

export function creerTournoi(entree: NouveauTournoi): Promise<Tournoi> {
  return fetchJson<Tournoi>('/api/v1/tournois', {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function getTournois(): Promise<Tournoi[]> {
  return fetchJson<Tournoi[]>('/api/v1/tournois')
}

export function modifierTournoi(id: number, entree: ModifierTournoi): Promise<Tournoi> {
  return fetchJson<Tournoi>(`/api/v1/tournois/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function demarrerTournoi(id: number): Promise<Tournoi> {
  return fetchJson<Tournoi>(`/api/v1/tournois/${id}/demarrer`, { method: 'POST' })
}

export function terminerTournoi(id: number): Promise<Tournoi> {
  return fetchJson<Tournoi>(`/api/v1/tournois/${id}/terminer`, { method: 'POST' })
}

export function supprimerTournoi(id: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${id}`, { method: 'DELETE' })
}

export function ajouterArcher(tournoiId: number, entree: NouvelArcher): Promise<Archer> {
  return fetchJson<Archer>(`/api/v1/tournois/${tournoiId}/archers`, {
    method: 'POST',
    body: JSON.stringify(entree),
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
