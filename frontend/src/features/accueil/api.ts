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

// Ce que le déroulé du tournoi exige d'inscrits, et ce qu'il en a (E05US021).
//
// `minimum` vaut 0 quand aucun déroulé n'est composé — il n'y a alors rien à exiger.
// `ordre_phase` / `rang_debut` disent **pourquoi** (« la phase 3 prélève à partir du rang 33 ») et
// sont nuls quand le manque ne vient d'aucun prélèvement en particulier.
// `origine` dit d'où vient le chiffre : `deroule` = plancher déduit des phases, `club` = règle
// saisie sur le format, `aucune` = rien de composé. C'est ce qui décide de la **phrase** affichée ;
// le déduire de `ordre_phase === null` faisait annoncer une règle de club là où il n'y en a pas.
export type OrigineExigence = 'aucune' | 'deroule' | 'club'

export interface ExigenceEffectif {
  inscrits: number
  minimum: number
  suffisant: boolean
  origine: OrigineExigence
  ordre_phase: number | null
  rang_debut: number | null
}

export function getExigenceEffectif(tournoiId: number): Promise<ExigenceEffectif> {
  return fetchJson<ExigenceEffectif>(`/api/v1/tournois/${tournoiId}/exigence-effectif`)
}
