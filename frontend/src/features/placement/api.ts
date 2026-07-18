// Accès API de la feature « placement » (E03US004, ADR-0024) : ajustement manuel du plan de cibles
// d'un départ. Miroir des DTO exposés par `api/v1/placement.py`.
//
// Le plan associe des **inscriptions** à des positions de cibles. La lecture renvoie le plan
// **persisté** (jamais recalculé à la volée) : cibles remplies + réserve (les `conflits`). Les
// écritures — régénérer/annuler, déplacer/échanger/mettre en réserve, placer les restants — sont
// réservées à l'admin côté serveur et renvoient le plan à jour.

import { fetchJson } from '../../shared/api/client'

// Pourquoi un archer est en réserve (non posé) : `sans_blason` (aucun blason pour tirer),
// `non_place` (aucune cible ne peut l'accueillir), `en_reserve` (en attente d'un placement).
// Vocabulaire **fermé**, miroir de l'enum `RaisonConflit` du domaine.
export type RaisonConflit = 'sans_blason' | 'non_place' | 'en_reserve'

// Un archer posé sur une cible : sa position (lettre « A »…« D ») et le blason sur lequel il tire.
export interface Placement {
  position: string
  archer_id: number
  blason_id: number
}

// Une cible du plan : son rang (`index`), son plafond d'archers (`capacite`) et les archers posés
// (`placements`, vide si la cible est libre).
export interface CiblePlacee {
  index: number
  capacite: number
  placements: Placement[]
}

// Un archer que le placement n'a pas pu poser (il est **dans la réserve**), et pourquoi.
export interface Conflit {
  archer_id: number
  raison: RaisonConflit
}

export interface PlanDeCibles {
  depart_id: number
  cibles: CiblePlacee[]
  conflits: Conflit[]
}

// Destination d'un déplacement : une case (`cible_index` + `position`) ou la **réserve**
// (`cible_index: null`). Une case libre déplace ; une case occupée échange atomiquement.
export interface Destination {
  cible_index: number | null
  position: string | null
}

const basePlan = (tournoiId: number, departId: number) =>
  `/api/v1/tournois/${tournoiId}/departs/${departId}/plan-de-cibles`

export function getPlanDeCibles(tournoiId: number, departId: number): Promise<PlanDeCibles> {
  return fetchJson<PlanDeCibles>(basePlan(tournoiId, departId))
}

// Régénère le plan auto (déterministe). Sert **aussi** à « annuler les modifications » : l'auto
// écrase les ajustements manuels (ADR-0024). Confirmation demandée côté UI avant l'appel.
export function regenererPlan(tournoiId: number, departId: number): Promise<PlanDeCibles> {
  return fetchJson<PlanDeCibles>(`${basePlan(tournoiId, departId)}/regenerer`, { method: 'POST' })
}

// Déplace / échange / met en réserve un inscrit. `409 deplacement_invalide` si le geste viole une
// contrainte (état serveur **inchangé**) : le client affiche le message et refetch le plan.
export function deplacerInscription(
  tournoiId: number,
  departId: number,
  inscriptionId: number,
  destination: Destination,
): Promise<PlanDeCibles> {
  return fetchJson<PlanDeCibles>(`${basePlan(tournoiId, departId)}/inscriptions/${inscriptionId}`, {
    method: 'PUT',
    body: JSON.stringify(destination),
  })
}

// Place automatiquement la réserve dans les trous du plan. Les archers qu'aucune cible ne peut
// prendre (sans blason, hauteur incompatible) restent en réserve.
export function placerRestants(tournoiId: number, departId: number): Promise<PlanDeCibles> {
  return fetchJson<PlanDeCibles>(`${basePlan(tournoiId, departId)}/placer-restants`, {
    method: 'POST',
  })
}
