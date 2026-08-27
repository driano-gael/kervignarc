// Accès HTTP du **système suisse** (E05US030) — miroir des DTO de `api/v1/suisse.py`.
//
// Même partage des rôles que les poules (ADR-0083) : deux **lectures** ici, et **aucune écriture**
// — une rencontre de ronde *est* un duel ordinaire (§7), donc elle s'écrit par les hooks de
// `features/saisie-duels` avec la famille `'suisse'`, ce qui lui donne gratuitement l'idempotence,
// la file hors-ligne et le rejeu. ⚠️ **Deux vues, deux DTO** : la vue de saisie porte le duel
// entier — chaque flèche, le barrage, les zones, le nom du validateur —, et rien de cela n'a à
// circuler sur une route anonyme (règle 6).

import { fetchJson } from '../../shared/api/client'
import type { Duel, Duelliste } from '../saisie-duels/api'
import type { Place } from '../../shared/salle/place'

/** Ce que la pose du plan n'a pas pu faire, et pourquoi — rapporté, jamais tu (ADR-0024).
 *
 * ⚠️ Le champ s'appelle `groupe` et non `poule` (le DTO jumeau des poules dit `poule`) : un suisse
 * n'a pas de groupes, son unique bloc porte le numéro 1. Le type est donc **distinct** de `Conflit`
 * malgré la ressemblance — les réutiliser l'un pour l'autre ferait lire `undefined` à l'écran. */
export interface ConflitSuisse {
  groupe: number
  raison: string
}

/** Une rencontre de ronde, prête pour le pavé. `couloirs` est `null` si le plan n'est pas posé. */
export interface RencontreSuisse {
  numero: number
  ronde: number
  couloirs: [Place, Place] | null
  haut: Duelliste | null
  bas: Duelliste | null
  duel: Duel
  /** Un tir existe en base mais oppose d'autres duellistes — la population a bougé sous un score
   * déjà saisi. Le serveur le masque et refuse de l'écraser : la rencontre est **bloquée**. */
  desynchronisee: boolean
}

/** La même rencontre **en consultation** : l'avancement, jamais le détail de saisie. */
export interface RencontreSuissePublique {
  numero: number
  ronde: number
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

/** Une ronde : ses rencontres, son porteur de bye, et si elle est **close**.
 *
 * `close` est ce dont l'écran a besoin pour dire pourquoi la ronde suivante n'est pas là : le
 * moteur refuse d'apparier par-dessus une ronde en cours. Une ronde ouverte n'est pas une anomalie,
 * c'est le régime normal d'une ronde en cours de saisie. */
export interface Ronde {
  numero: number
  rencontres: RencontreSuisse[]
  bye: Duelliste | null
  close: boolean
}

/** La même ronde **en consultation**. */
export interface RondePublique extends Omit<Ronde, 'rencontres'> {
  rencontres: RencontreSuissePublique[]
}

/** Une ligne du classement provisoire.
 *
 * ⚠️ `rang` suit la convention **« 1224 »** (deux ex æquo au rang 2 laissent le 3 vacant), et
 * `points` est en **demi-points doublés** : une victoire vaut 2, un nul 1 — le domaine évite le
 * flottant, dont les égalités approchées sont ce sur quoi un départage ne doit pas reposer.
 * `buchholz` est la somme des points des adversaires rencontrés.
 */
export interface RangSuisse {
  rang: number
  archer_id: number
  points: number
  buchholz: number
  ex_aequo: boolean
}

/** La photo d'une phase **avec le pavé** de chaque rencontre — réservée à la saisie (scoreur). */
export interface EtatSuisseSaisie {
  phase_id: number
  nb_rondes: number
  /** Le maximum appariable sans ré-affrontement sur l'effectif du jour. Rendu par le serveur et
   * **jamais recalculé ici** : deux arithmétiques pour une même règle divergent tôt ou tard. */
  rondes_maximales: number
  effectif: number
  rondes: Ronde[]
  classement: RangSuisse[]
  conflits: ConflitSuisse[]
}

/** La même photo **rédigée** — écran d'organisation, salle, public. */
export interface EtatSuissePublique extends Omit<EtatSuisseSaisie, 'rondes'> {
  rondes: RondePublique[]
}

export function getEtatSuisse(tournoiId: number, phaseId: number): Promise<EtatSuissePublique> {
  return fetchJson<EtatSuissePublique>(
    `/api/v1/suisse/etat/${tournoiId}/${phaseId}`,
    undefined,
    'aucune',
  )
}

/** L'état **de saisie** : jeton scoreur, et borné au tournoi du scoreur (403 sinon). */
export function getEtatSuisseSaisie(tournoiId: number, phaseId: number): Promise<EtatSuisseSaisie> {
  return fetchJson<EtatSuisseSaisie>(
    `/api/v1/suisse/saisie/${tournoiId}/${phaseId}`,
    undefined,
    'scoreur',
  )
}

/** Pose (ou repose) le plan de couloirs de la phase — **action admin**, jeton Bearer.
 *
 * Un **seul** bloc pour toute la phase, à la différence des poules qui en posent un par groupe :
 * une ronde apparie tout le plateau d'un coup, il n'y a pas de groupe à distinguer. */
export function regenererPlanSuisse(
  tournoiId: number,
  phaseId: number,
): Promise<EtatSuissePublique> {
  return fetchJson<EtatSuissePublique>(`/api/v1/suisse/plan/${tournoiId}/${phaseId}`, {
    method: 'POST',
  })
}
