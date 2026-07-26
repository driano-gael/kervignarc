// Accès API de la feature « plan de duels » (E03US009, ADR-0048) : ajustement manuel du placement
// des duellistes d'une **phase de tableau** (élimination directe). Miroir des DTO exposés par le
// backend (`api/v1/placement_duels.py`).
//
// Jumeau du plan de cibles de qualification (`placement/api.ts`), à deux différences métier près :
//  - on place les **duellistes** d'une **phase** (pas les inscrits d'un **départ**) ;
//  - le signal d'équité n'est pas la mixité de club mais l'**adjacence** : deux adversaires d'un
//    même duel doivent être placés **côte à côte** (`adjacence_non_garantie` au niveau cible).
// Autre différence structurelle : **aucune** confirmation d'impact (E12US007) — la régénération est
// directe (ADR-0048).

import { fetchJson } from '../../shared/api/client'

// Pourquoi un duelliste est en réserve (non posé), miroir de l'enum `RaisonConflit` du domaine :
// `sans_blason` (aucun blason pour tirer), `non_place` (aucune cible ne peut l'accueillir),
// `en_reserve` (en attente d'un placement). Vocabulaire **fermé**.
export type RaisonConflit = 'sans_blason' | 'non_place' | 'en_reserve'

// Un duelliste posé sur une cible : sa position (lettre « A »…« D »), le blason sur lequel il tire,
// et son `inscription_id` — la cible du `PUT` de déplacement. Le serveur l'expose directement pour
// éviter au client de reconstituer la correspondance archer → inscription.
export interface Placement {
  position: string
  archer_id: number
  blason_id: number
  inscription_id: number
}

// Une cible du plan de duels : son rang (`index`), son plafond (`capacite`) et les duellistes posés
// (`placements`, vide si la cible est libre).
//
// `adjacence_non_garantie` (E03US009) : `true` quand la cible porte au moins un duel dont les deux
// adversaires ne sont pas placés **côte à côte**. L'admin le voit pour ajuster à la main ; ce n'est
// **pas** une erreur, juste un objectif d'organisation non atteint. Recalculé serveur à chaque
// lecture (jamais persisté).
export interface CiblePlaceeDuel {
  index: number
  capacite: number
  placements: Placement[]
  adjacence_non_garantie: boolean
}

// Un duelliste que le placement n'a pas pu poser (il est **dans la réserve**), et pourquoi. Porte
// aussi son `inscription_id` : pour le reposer par glisser-déposer depuis la réserve.
export interface Conflit {
  archer_id: number
  raison: RaisonConflit
  inscription_id: number
}

// Un duel dont les deux adversaires ne sont **pas** côte à côte (séparés). Sert au décompte de la
// bannière récapitulative : c'est le nombre de **duels** séparés, plus juste que le nombre de cibles
// signalées (une cible peut porter plusieurs duels).
export interface DuelSepare {
  archer_a: number
  archer_b: number
}

export interface PlanDeDuels {
  phase_id: number
  cibles: CiblePlaceeDuel[]
  conflits: Conflit[]
  duels_separes: DuelSepare[]
}

// Destination d'un déplacement : une case (`cible_index` + `position`) ou la **réserve**
// (`cible_index: null`). Une case libre déplace ; une case occupée échange atomiquement.
export interface Destination {
  cible_index: number | null
  position: string | null
}

const base = (tournoiId: number, phaseId: number) =>
  `/api/v1/tournois/${tournoiId}/phases/${phaseId}/plan-de-duels`

export function getPlanDeDuels(tournoiId: number, phaseId: number): Promise<PlanDeDuels> {
  return fetchJson<PlanDeDuels>(base(tournoiId, phaseId))
}

// Régénère le plan auto (déterministe). Sert **aussi** à « annuler les modifications » : l'auto
// écrase les ajustements manuels. Contrairement à la qualification (E12US007), **aucune**
// confirmation d'impact : POST **sans corps** (ADR-0048).
export function regenererPlanDuels(tournoiId: number, phaseId: number): Promise<PlanDeDuels> {
  return fetchJson<PlanDeDuels>(`${base(tournoiId, phaseId)}/regenerer`, {
    method: 'POST',
  })
}

// Déplace / échange / met en réserve un duelliste. `409 deplacement_invalide` si le geste viole une
// contrainte (état serveur **inchangé**) : le client affiche le message et refetch le plan.
export function deplacerDuelliste(
  tournoiId: number,
  phaseId: number,
  inscriptionId: number,
  destination: Destination,
): Promise<PlanDeDuels> {
  return fetchJson<PlanDeDuels>(`${base(tournoiId, phaseId)}/inscriptions/${inscriptionId}`, {
    method: 'PUT',
    body: JSON.stringify(destination),
  })
}

// Place automatiquement la réserve dans les trous du plan. Les duellistes qu'aucune cible ne peut
// prendre (sans blason, incompatibilité) restent en réserve.
export function placerRestantsDuels(tournoiId: number, phaseId: number): Promise<PlanDeDuels> {
  return fetchJson<PlanDeDuels>(`${base(tournoiId, phaseId)}/placer-restants`, {
    method: 'POST',
  })
}
