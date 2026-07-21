// Accès API de la complétude du tournoi (E12US005). Miroir des DTO de `api/v1/completude.py`.
// Route **admin** (portée `'admin'` par défaut de `fetchJson`, en-tête `Authorization: Bearer`).

import { fetchJson } from '../../shared/api/client'

// Les quatre états d'une ligne (miroir de `domain.completude.EtatSection`) :
//  - `ok` : terminé ;  `alerte` : commencé mais incomplet (le « ! » du CDC UX §8.3) ;
//  - `en_attente` : rien d'exploitable encore ;  `a_venir` : pas encore géré (phases, EPIC-05).
export type EtatSection = 'ok' | 'alerte' | 'en_attente' | 'a_venir'

export interface LigneCompletude {
  cle: string
  libelle: string
  etat: EtatSection
  fait: number | null // null pour les lignes sans décompte (phases, classement)
  total: number | null
}

export interface Completude {
  sportif: LigneCompletude[]
  hors_sportif: LigneCompletude[]
  sportif_complet: boolean
}

export function getCompletude(tournoiId: number): Promise<Completude> {
  return fetchJson<Completude>(`/api/v1/tournois/${tournoiId}/completude`)
}
