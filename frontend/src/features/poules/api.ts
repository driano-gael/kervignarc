// Accès HTTP des **poules** (E05US023, ADR-0083) — miroir des DTO de `api/v1/poules.py`.
//
// Deux lectures seulement ici : la **répartition** (ce que le réglage produit sur l'effectif réel,
// sans exiger salle ni plan) et l'**état** de la phase (groupes, blocs de couloirs, rencontres par
// tour, classements, barrages requis). Les **écritures** ne vivent pas dans cette feature : une
// rencontre de poule est un duel ordinaire (ADR-0083 §7), donc elle s'écrit par les hooks de
// `features/saisie-duels`, avec la famille `'poule'` — c'est ce qui lui donne gratuitement
// l'idempotence, la file hors-ligne et le rejeu.
//
// Lectures en portée `'aucune'` : l'état d'une phase de poules est une consultation, comme le
// tableau public ou le classement (E10US001). Le serveur reste l'autorité.

import { fetchJson } from '../../shared/api/client'
import type { Duel, Duelliste } from '../saisie-duels/api'

/** Une place de tir : `[cible, couloir]` — le couloir est une lettre (`A`…`D`). */
export type Place = [number, string]

/** Ce que le réglage produit sur l'effectif du jour — le CA « la répartition est montrée ». */
export interface Repartition {
  effectif: number
  taille_visee: number
  nb_poules: number
  tailles: number[]
}

/** Une rencontre, prête pour le pavé de saisie de duel. `couloirs` est `null` si le plan manque. */
export interface Rencontre {
  numero: number
  poule: number
  tour: number
  couloirs: [Place, Place] | null
  duel: Duel
}

/** Une ligne du classement d'une poule — les cinq critères du §10.1, pour un départage traçable. */
export interface RangPoule {
  rang: number
  archer_id: number
  points_match: number
  diff_sets: number
  diff_score: number
  nb_dix: number
  nb_neuf: number
  ex_aequo: boolean
}

/** Une poule : ses membres, son bloc de couloirs, ses rencontres, son classement.
 *
 * `barrage_requis` porte le régime d'ex æquo (ADR-0083 §5) : la poule qui *classe* départage tout
 * ex æquo irréductible, celle qui *qualifie* ne départage que la barre. C'est ce champ qui déclenche
 * l'annonce à l'écran ; le barrage lui-même se tire depuis le panneau de barrages (E06US003). */
export interface Poule {
  numero: number
  membres: Duelliste[]
  bloc: Place[] | null
  rencontres: Rencontre[]
  classement: RangPoule[]
  qualifies: Duelliste[]
  barrage_requis: boolean
}

/** Une poule composée qu'aucun bloc ne porte — plan non posé, ou salle trop petite. */
export interface Conflit {
  poule: number
  raison: string
}

export interface EtatPoules {
  phase_id: number
  repartition: Repartition
  poules: Poule[]
  conflits: Conflit[]
}

export function getEtatPoules(tournoiId: number, phaseId: number): Promise<EtatPoules> {
  return fetchJson<EtatPoules>(`/api/v1/poules/etat/${tournoiId}/${phaseId}`, undefined, 'aucune')
}

export function getRepartition(tournoiId: number, phaseId: number): Promise<Repartition> {
  return fetchJson<Repartition>(
    `/api/v1/poules/repartition/${tournoiId}/${phaseId}`,
    undefined,
    'aucune',
  )
}

/** Pose (ou repose) le plan de couloirs de la phase — **action admin**, jeton Bearer. */
export function regenererPlanPoules(tournoiId: number, phaseId: number): Promise<EtatPoules> {
  return fetchJson<EtatPoules>(`/api/v1/poules/plan/${tournoiId}/${phaseId}/regenerer`, {
    method: 'POST',
  })
}
