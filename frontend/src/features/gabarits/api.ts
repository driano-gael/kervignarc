// Accès API de la feature « gabarits de salle » (E01US007) : CRUD des gabarits réutilisables.
// Miroir des DTO exposés par `api/v1/gabarits.py`. Ressource **autonome** (non rattachée à un
// tournoi) : pas d'identifiant de tournoi dans les routes.

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
  cibles: CibleGabarit[]
}

export interface NouveauGabarit {
  nom: string
  nb_cibles: number
  // Plafond appliqué à toutes les cibles (défaut serveur : 4).
  capacite?: number
}

// L'édition porte sur les mêmes champs que la création.
export type ModifierGabarit = NouveauGabarit

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
