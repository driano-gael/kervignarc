// Accès API du pilotage d'un tour (E12US002, ADR-0056). Miroir des DTO de `api/v1/pilotage.py`.
// Feu vert (état de préparation, duel par duel), impact (le chiffrage du bouton) et lancement sont
// des routes **admin** (portée `'admin'` par défaut de `fetchJson`, en-tête `Authorization: Bearer`).

import { fetchJson } from '../../shared/api/client'

export interface Duelliste {
  archer_id: number
  nom: string
  prenom: string
}

// Un duel **à venir** (non tranché) et son état de préparation : les trois questions du CA, plus le
// blocage **nommé** (« en attente du duel n°3 », « cible non attribuée ») quand il n'est pas prêt.
export interface DuelAVenir {
  numero: number
  tour: number
  haut: Duelliste | null
  bas: Duelliste | null
  participants_connus: boolean
  cible_haut: number | null
  cible_bas: number | null
  cible_attribuee: boolean
  sources_en_attente: number[]
  pret_a_lancer: boolean
  blocage: string | null
}

export interface FeuVert {
  phase_id: number
  est_termine: boolean
  duels: DuelAVenir[]
  nb_prets: number
}

// Ce que le bouton chiffre (et ce que le lancement a émis) : duels, cibles, archers concernés.
export interface ResumeLancement {
  phase_id: number
  numeros: number[]
  cibles: number[]
  nb_duels: number
  nb_archers: number
}

export function getFeuVert(tournoiId: number, phaseId: number): Promise<FeuVert> {
  return fetchJson<FeuVert>(`/api/v1/pilotage/feu-vert/${tournoiId}/${phaseId}`)
}

export function getImpactLancement(tournoiId: number, phaseId: number): Promise<ResumeLancement> {
  return fetchJson<ResumeLancement>(`/api/v1/pilotage/impact-lancement/${tournoiId}/${phaseId}`)
}

// Le geste : fait partir les duels prêts (lancement global). Le serveur recalcule le feu vert et
// n'émet que les prêts ; renvoie le décompte réellement lancé. `numeros` (sous-ensemble) omis =
// tous les prêts (`D-23`), suffisant pour l'écran ; l'API accepte un sous-ensemble si besoin.
export function lancerTour(tournoiId: number, phaseId: number): Promise<ResumeLancement> {
  return fetchJson<ResumeLancement>('/api/v1/pilotage/lancer', {
    method: 'POST',
    body: JSON.stringify({ tournoi_id: tournoiId, phase_id: phaseId }),
  })
}
