// Accès API de la feature « gabarits de salle » (E01US007, E01US008).
// Miroir des DTO exposés par `api/v1/gabarits.py`. Deux familles :
// - la **bibliothèque** de modèles réutilisables (routes à plat `/gabarits`) ;
// - le **plan de salle d'un tournoi** (routes `/tournois/{id}/gabarit`) : appliquer un modèle
//   (copie), lire et ajuster la copie sans altérer le modèle.

import { fetchJson } from '../../shared/api/client'

export interface CibleGabarit {
  index: number
  // Plafond d'archers de la cible (1 à 4) ; positions déduites.
  capacite: number
  positions: string[]
}

export interface Gabarit {
  id: number
  nom: string
  nb_cibles: number
  // `null` pour un modèle de bibliothèque ; l'identifiant du tournoi pour une instance appliquée.
  tournoi_id: number | null
  cibles: CibleGabarit[]
}

export interface NouveauGabarit {
  nom: string
  nb_cibles: number
  // Plafond appliqué à toutes les cibles (défaut serveur : 4).
  capacite?: number
}

// L'édition d'un modèle porte sur les mêmes champs que la création.
export type ModifierGabarit = NouveauGabarit

// Ajustement du plan d'un tournoi : nom + plafond **cible par cible** (le nombre de valeurs fixe
// le nombre de cibles).
export interface AjustementGabarit {
  nom: string
  capacites: number[]
}

export function getGabarits(): Promise<Gabarit[]> {
  return fetchJson<Gabarit[]>('/api/v1/gabarits')
}

export function creerGabarit(entree: NouveauGabarit): Promise<Gabarit> {
  return fetchJson<Gabarit>('/api/v1/gabarits', {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function modifierGabarit(id: number, entree: ModifierGabarit): Promise<Gabarit> {
  return fetchJson<Gabarit>(`/api/v1/gabarits/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function supprimerGabarit(id: number): Promise<void> {
  return fetchJson<void>(`/api/v1/gabarits/${id}`, { method: 'DELETE' })
}

// --- Plan de salle d'un tournoi (E01US008) ---

// Le gabarit appliqué au tournoi, ou `null` s'il n'y en a pas encore.
export function getGabaritDuTournoi(tournoiId: number): Promise<Gabarit | null> {
  return fetchJson<Gabarit | null>(`/api/v1/tournois/${tournoiId}/gabarit`)
}

// Applique un modèle de la bibliothèque au tournoi (crée/remplace sa copie ajustable).
export function appliquerGabarit(tournoiId: number, modeleId: number): Promise<Gabarit> {
  return fetchJson<Gabarit>(`/api/v1/tournois/${tournoiId}/gabarit`, {
    method: 'PUT',
    body: JSON.stringify({ modele_id: modeleId }),
  })
}

// Ajuste la copie du tournoi (nom + plafond cible par cible) sans toucher au modèle d'origine.
export function ajusterGabarit(tournoiId: number, entree: AjustementGabarit): Promise<Gabarit> {
  return fetchJson<Gabarit>(`/api/v1/tournois/${tournoiId}/gabarit`, {
    method: 'PATCH',
    body: JSON.stringify(entree),
  })
}
