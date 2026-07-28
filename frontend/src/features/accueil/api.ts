// Accès API de l'accueil-tableau de bord (E14US001). Deux usages du cycle de vie du tournoi :
//  - **lire** les transitions offertes par le statut courant (la frise en fait ses boutons) ;
//  - **appliquer** une transition, de façon **générique** : `nom` est le suffixe d'endpoint
//    (`vers-pret`, `demarrer`, …), aligné sur la topologie exposée (ADR-0026 §2).
// Miroir des DTO de `api/v1/tournois.py`. Routes admin (portée 'admin' par défaut de `fetchJson`).

import { fetchJson } from '../../shared/api/client'
import type { StatutTournoi, Tournoi } from '../competition/api'

// Une transition **offerte** par le statut courant. `nom` sert d'identifiant **et** de route.
export interface Transition {
  nom: string
  libelle: string
  vers: StatutTournoi
}

export function getTransitions(tournoiId: number): Promise<Transition[]> {
  return fetchJson<Transition[]>(`/api/v1/tournois/${tournoiId}/transitions`)
}

// Applique la transition `nom` (POST du suffixe d'endpoint). La **garde** reste au serveur : une
// transition listée peut échouer (ex. `vers-pret` sans départ → 409), l'erreur remonte au client.
export function transitionnerTournoi(tournoiId: number, nom: string): Promise<Tournoi> {
  return fetchJson<Tournoi>(`/api/v1/tournois/${tournoiId}/${nom}`, { method: 'POST' })
}
