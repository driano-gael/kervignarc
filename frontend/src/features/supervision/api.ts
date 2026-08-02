// Accès API de la console de supervision (E12US001, ADR-0038). Miroir des DTO de
// `api/v1/supervision.py`. Console et révocation sont des routes **admin** (portée `'admin'` par
// défaut de `fetchJson`, en-tête `Authorization: Bearer`).

import { fetchJson } from '../../shared/api/client'
import type { Prise } from '../ecrans/api'
import type { TypePoste } from '../../shared/stores/sessionPosteStore'
import type { EtatPoste } from './etat'

export interface Avancement {
  volee_courante: number
  nb_volees: number
}

export interface PosteSupervision {
  poste_id: number
  /** `cible` ou `ecran` (E07US004) : les deux natures se lisent dans **le même** tableau, parce que
   * c'est là que le CA veut qu'on découvre un écran figé — *« un écran figé ne se plaint pas, seule
   * la supervision le révèle »*. */
  type: TypePoste
  cible_index: number | null
  libelle: string | null
  etat: EtatPoste
  derniere_saisie: string | null // ISO UTC, ou null si rien saisi
  ip: string | null // diagnostic (D-06), null si non rattaché
  avancement: Avancement | null // null si non rattaché ou sans départ courant
  /** La prise de contrôle en vigueur sur cet écran, ou `null`. Toujours `null` pour une cible. */
  prise: Prise | null
}

export interface Supervision {
  postes: PosteSupervision[]
  /** Compteurs des **tablettes seules** : c'est l'indicateur « 28/30 » sur lequel l'organisateur
   * juge s'il peut lancer un tour. Un écran hors ligne n'empêche personne de tirer. */
  nb_en_ligne: number
  nb_total: number
  nb_ecrans_en_ligne: number
  nb_ecrans: number
}

export function getSupervision(tournoiId: number): Promise<Supervision> {
  return fetchJson<Supervision>(`/api/v1/tournois/${tournoiId}/supervision`)
}

export function revoquerPoste(tournoiId: number, posteId: number): Promise<void> {
  // 204 attendu (fetchJson renvoie undefined) : ferme les sessions du poste et oublie sa présence.
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/postes/${posteId}/revocation`, {
    method: 'POST',
  })
}
