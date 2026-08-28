// Accès HTTP des **poules** (E05US023, ADR-0083) — miroir des DTO de `api/v1/poules.py`.
//
// Deux lectures seulement : la **répartition** et l'**état** de la phase. Les **écritures** ne
// vivent pas ici — une rencontre de poule est un duel ordinaire (ADR-0083 §7), donc elle passe par
// `features/saisie-duels` avec la famille `'poule'`, ce qui lui donne idempotence, file hors-ligne
// et rejeu. ⚠️ **Deux vues, deux DTO** : `/etat` (portée `'aucune'`) est **restreint** — ni
// flèches, ni barrage interne, ni nom du validateur ; `/saisie` (portée `'scoreur'`) porte le duel
// entier. La première version servait le DTO scoreur sur la route anonyme.

import { fetchJson } from '../../shared/api/client'
import type { Duel, Duelliste } from '../saisie-duels/api'

// `Place` a été **remontée dans `shared/salle/`** en revue d'E05US030 : `features/suisse` en avait
// besoin, et une feature n'importe pas d'une feature sœur (règle 10). Ré-exportée ici pour ne
// casser aucun import existant.
import type { Place } from '../../shared/salle/place'
import type { ModeDeComposition } from '../../shared/phases/poules'

export type { Place }

/** Ce que le réglage produit sur l'effectif du jour — le CA « la répartition est montrée ». */
export interface Repartition {
  effectif: number
  taille_visee: number
  nb_poules: number
  tailles: number[]
  /** Comment les groupes ont été composés (E05US029) — absent des réponses d'avant cette US. */
  mode?: ModeDeComposition
}

/** Une rencontre, prête pour le pavé de saisie de duel. `couloirs` est `null` si le plan manque. */
export interface Rencontre {
  numero: number
  poule: number
  tour: number
  couloirs: [Place, Place] | null
  duel: Duel
  /** Un tir existe en base mais oppose d'autres duellistes — la composition a bougé sous un score
   * déjà saisi. Le serveur le masque (ADR-0049 §4) et refuse de l'écraser : la rencontre est donc
   * **bloquée**, pas « à tirer ». */
  desynchronisee: boolean
}

/** La même rencontre **en consultation** : l'avancement, jamais le détail de saisie.
 *
 * `termine` et `validee` disent deux choses distinctes — le tir est allé au bout / le scoreur a
 * scellé —, et c'est entre les deux que s'affiche « en attente de validation ». */
export interface RencontrePublique {
  numero: number
  poule: number
  tour: number
  couloirs: [Place, Place] | null
  haut: Duelliste | null
  bas: Duelliste | null
  points_haut: number | null
  points_bas: number | null
  vainqueur: string | null
  termine: boolean
  validee: boolean
  desynchronisee: boolean
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

/** La même poule **en consultation**. Tout est identique sauf le détail de saisie des rencontres :
 * composition, bloc, classement complet et drapeau de barrage n'ont rien de confidentiel. */
export interface PoulePublique extends Omit<Poule, 'rencontres'> {
  rencontres: RencontrePublique[]
}

/** La photo d'une phase, **en consultation** — ce que lit l'écran d'organisation et la salle. */
export interface EtatPoules {
  phase_id: number
  repartition: Repartition
  poules: PoulePublique[]
  conflits: Conflit[]
}

/** La même photo **avec le pavé** de chaque rencontre — réservée à la saisie (scoreur). */
export interface EtatPoulesSaisie {
  phase_id: number
  repartition: Repartition
  poules: Poule[]
  conflits: Conflit[]
}

export function getEtatPoules(tournoiId: number, phaseId: number): Promise<EtatPoules> {
  return fetchJson<EtatPoules>(`/api/v1/poules/etat/${tournoiId}/${phaseId}`, undefined, 'aucune')
}

/** L'état **de saisie** : jeton scoreur, et borné au tournoi du scoreur (403 sinon). */
export function getEtatPoulesSaisie(tournoiId: number, phaseId: number): Promise<EtatPoulesSaisie> {
  return fetchJson<EtatPoulesSaisie>(
    `/api/v1/poules/saisie/${tournoiId}/${phaseId}`,
    undefined,
    'scoreur',
  )
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
