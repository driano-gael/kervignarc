// Accès HTTP de la **colline** (E05US027) — miroir des DTO de `api/v1/colline.py`.
//
// Même partage des rôles que les poules et le suisse (ADR-0083) : deux **lectures** ici — l'état
// rédigé (`/etat`, ouvert) et l'état de saisie (`/saisie`, scoreur) —, et **aucune écriture**. Un
// défi *est* un duel ordinaire (ADR-0083 §7) : il s'écrit par les hooks de `features/saisie-duels`
// avec la famille `'colline'`, ce qui lui donne gratuitement l'idempotence, la file hors-ligne et
// le rejeu.
//
// **Deux vues, deux DTO**, et la raison n'est pas cosmétique : la vue de saisie porte le duel
// entier — chaque flèche, le barrage, les zones du pavé, le nom du bénévole validateur. Rien de
// cela n'a à circuler sur une route anonyme (règle 6).

import { fetchJson } from '../../shared/api/client'
import type { Duel, Duelliste } from '../saisie-duels/api'
import type { Place } from '../../shared/salle/place'

/** Ce que la pose du plan n'a pas pu faire, et pourquoi — rapporté, jamais tu (ADR-0024).
 *
 * ⚠️ Le champ s'appelle `groupe` et non `poule`, comme chez le suisse et pour la même raison : une
 * colline n'a pas de groupes, son unique bloc porte le numéro 1. */
export interface ConflitColline {
  groupe: number
  raison: string
}

/** Un défi, prêt pour le pavé. `couloirs` est `null` si le plan n'est pas posé.
 *
 * `position_haute` est celle du **défié** (le mieux placé, qui a quelque chose à perdre) et
 * `position_basse` celle du **challenger** (qui monte s'il l'emporte). Ce sont des positions dans
 * la colline, 1-indexées — « le 6 défie le 4 » —, pas des numéros de match : c'est ce que le
 * spectateur suit. */
export interface Defi {
  numero: number
  manche: number
  position_haute: number
  position_basse: number
  couloirs: [Place, Place] | null
  haut: Duelliste | null
  bas: Duelliste | null
  duel: Duel
  /** Un tir existe en base mais oppose d'autres duellistes — la population a bougé sous un score
   * déjà saisi. Le serveur le masque et refuse de l'écraser : le défi est **bloqué**. */
  desynchronisee: boolean
}

/** Le même défi **en consultation** : l'avancement, jamais le détail de saisie. */
export interface DefiPublic {
  numero: number
  manche: number
  position_haute: number
  position_basse: number
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

/** Une manche : ses défis, ses archers **au repos**, et si elle est **close**.
 *
 * `close` est ce dont l'écran a besoin pour dire pourquoi la manche suivante n'est pas là : les
 * défis de la manche `n+1` se calculent sur les **positions** issues de la manche `n`, donc tant
 * qu'un défi n'est pas tranché, ces positions n'existent pas. Une manche ouverte n'est pas une
 * anomalie, c'est le régime normal d'une manche en cours de saisie.
 *
 * ⚠️ **`au_repos` n'est pas décoratif, et ce n'est pas le « bye » du suisse.** Un bye est un
 * archer désigné qui gagne d'office ; ici personne ne gagne rien — à portée 1, les **deux**
 * extrémités de la colline ne tirent pas de la manche, quel que soit l'effectif. Sans cette liste,
 * elles disparaissent de la manche sans explication et le scoreur les cherche. */
export interface Manche {
  numero: number
  defis: Defi[]
  au_repos: Duelliste[]
  close: boolean
}

/** La même manche **en consultation**. */
export interface manchePublique extends Omit<Manche, 'defis'> {
  defis: DefiPublic[]
}

/** Une position de la colline — le classement, qui **est** l'état courant du format.
 *
 * ⚠️ **Ni rang sportif ni ex æquo**, à la différence du suisse : deux archers n'occupent jamais la
 * même position. La position affichée et celle que lit un prélèvement coïncident donc, et aucune
 * égalité ne peut retenir une phase avale (ADR-0081). */
export interface RangColline {
  position: number
  archer_id: number
}

/** La photo d'une phase **avec le pavé** de chaque défi — réservée à la saisie (scoreur). */
export interface EtatCollineSaisie {
  phase_id: number
  nb_manches: number
  /** Ce que l'organisateur a **réglé** : 1 = King of the Hill, 2+ = Ladder. */
  portee_de_defi: number
  /** La portée maximale que l'effectif du jour autorise (`effectif - 1`). Rendue par le serveur et
   * **jamais recalculée ici** : deux arithmétiques pour une même règle divergent tôt ou tard. */
  portee_maximale: number
  effectif: number
  manches: Manche[]
  classement: RangColline[]
  conflits: ConflitColline[]
}

/** La même photo **rédigée** — écran d'organisation, salle, public. */
export interface EtatCollinePublique extends Omit<EtatCollineSaisie, 'manches'> {
  manches: manchePublique[]
}

export function getEtatColline(tournoiId: number, phaseId: number): Promise<EtatCollinePublique> {
  return fetchJson<EtatCollinePublique>(
    `/api/v1/colline/etat/${tournoiId}/${phaseId}`,
    undefined,
    'aucune',
  )
}

/** L'état **de saisie** : jeton scoreur, et borné au tournoi du scoreur (403 sinon). */
export function getEtatCollineSaisie(
  tournoiId: number,
  phaseId: number,
): Promise<EtatCollineSaisie> {
  return fetchJson<EtatCollineSaisie>(
    `/api/v1/colline/saisie/${tournoiId}/${phaseId}`,
    undefined,
    'scoreur',
  )
}

/** Pose (ou repose) le plan de couloirs de la phase — **action admin**, jeton Bearer.
 *
 * Un **seul** bloc pour toute la phase, comme le suisse : une manche apparie sur tout le plateau,
 * il n'y a pas de groupe à distinguer. Le bloc est dimensionné sur la manche la plus chargée, donc
 * certaines manches y laissent des couloirs vides — c'est voulu, redimensionner en cours de phase
 * déplacerait les archers déjà installés. */
export function regenererPlanColline(
  tournoiId: number,
  phaseId: number,
): Promise<EtatCollinePublique> {
  return fetchJson<EtatCollinePublique>(`/api/v1/colline/plan/${tournoiId}/${phaseId}`, {
    method: 'POST',
  })
}
