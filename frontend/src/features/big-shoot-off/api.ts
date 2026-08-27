// Accès HTTP du **Big Shoot Off** (E05US028) — miroir des DTO de `api/v1/big_shoot_off.py`.
//
// ⚠️ **Les écritures vivent ici**, contrairement aux poules : une volée de Big Shoot Off est
// **collective** et n'a pas d'adversaire, donc le pavé de duel ne s'y applique pas et il n'existe
// aucun hook de tir de série à emprunter. Les deux écritures rendent l'**état complet** plutôt que
// l'objet écrit : une manche validée peut éliminer, donc changer la lice de tout le monde — rendre
// la volée seule laisserait une fenêtre où l'écran montre un archer sorti comme encore en lice.

import { fetchJson } from '../../shared/api/client'

/** Ce que la liste de sortants donne sur l'effectif du jour — le CA « la projection est montrée ». */
export interface Projection {
  effectif: number
  eliminations: number[]
  paliers: number[]
  /** Le format du tir — l'écran de saisie en a besoin pour savoir combien de champs de flèche
   * afficher. Le deviner avec un défaut en dur serait faux dès qu'un club règle autre chose. */
  volees: number
  fleches_par_volee: number
  restants: number
  manches_jouables: number
  manches_ignorees: number
}

/** Un finaliste : son sort et ce qu'il a marqué manche par manche.
 *
 * `rang` est `null` tant qu'il est **en lice** — un rang annoncé avant la sortie serait un faux
 * départ. `scores` ne porte que les manches **entièrement validées**. */
export interface Tireur {
  archer_id: number
  nom: string
  prenom: string
  en_lice: boolean
  rang: number | null
  scores: number[]
  // Le numéro de la **prochaine volée à saisir** pour cet archer, ou `null` s'il n'y a rien à tirer
  // (sorti, phase finie, ou barrage en cours). C'est le serveur qui le calcule : la manche *m*
  // occupe les volées `(m-1)·V+1 … m·V`, une numérotation qu'il persiste et que le front n'a pas à
  // re-dériver. Deviner « la première volée de la manche » n'était juste qu'à `volees = 1`, et
  // rendait la finale injouable dès `volees = 2` (revue d'E05US028).
  prochaine_volee: number | null
}

/** Une manche : son rang, combien elle élimine, où en est sa saisie. */
export interface Manche {
  numero: number
  elimine: number
  volees: number[]
  complete: boolean
  jouee: boolean
}

/** L'égalité qui **suspend** la phase. `places` dit combien des ex æquo sortent réellement. */
export interface BarrageEnAttente {
  archer_ids: number[]
  noms: string[]
  places: number
}

/** La photo d'un Big Shoot Off **avec l'adressage de saisie** — réservée au scoreur. */
export interface EtatBigShootOff {
  phase_id: number
  projection: Projection
  tireurs: Tireur[]
  manches: Manche[]
  termine: boolean
  barrage: BarrageEnAttente | null
}

/** La **forme** du format, telle qu'un spectateur la lit : « 12 → 8 → 6 → 5, 3 volées de 3 ».
 *
 * `Projection` amputée de ce qui appartient à l'atelier — `eliminations` (la liste réglée) et
 * `manches_ignorees` (le réglage dépasse l'effectif). Ce dernier n'est pas confidentiel, il est
 * **sans destinataire** devant une salle, et l'afficher ferait croire à un incident. */
export interface FormatBigShootOff {
  effectif: number
  paliers: number[]
  restants: number
  volees: number
  fleches_par_volee: number
  manches_jouables: number
}

/** Le même finaliste **en consultation** : son sort et ses manches validées, jamais la prochaine
 * volée à saisir — c'est une affordance de pavé, sans objet hors de la tablette. */
export interface TireurPublic {
  archer_id: number
  nom: string
  prenom: string
  en_lice: boolean
  rang: number | null
  scores: number[]
}

/** La même manche, sans les numéros de volée de la feuille de saisie. */
export interface ManchePublique {
  numero: number
  elimine: number
  complete: boolean
  jouee: boolean
}

/** La photo d'un Big Shoot Off **rédigée** — appli publique, écran de salle, écran d'organisation.
 *
 * ⚠️ **Cette forme n'existe que depuis E05US031.** Le Big Shoot Off était le seul des trois formats
 * sans arbre à n'avoir aucune surface de lecture ouverte : sa route `/etat/` était scoreur, et
 * l'onglet public restait donc muet pendant une finale. */
export interface EtatBigShootOffPublic {
  phase_id: number
  format: FormatBigShootOff
  tireurs: TireurPublic[]
  manches: ManchePublique[]
  termine: boolean
  barrage: BarrageEnAttente | null
}

/** L'état **en consultation** — contenu restreint, lecture ouverte. */
export function getEtatBigShootOff(
  tournoiId: number,
  phaseId: number,
): Promise<EtatBigShootOffPublic> {
  return fetchJson<EtatBigShootOffPublic>(
    `/api/v1/big-shoot-off/etat/${tournoiId}/${phaseId}`,
    undefined,
    'aucune',
  )
}

/** L'état **de saisie** — l'adressage du pavé en plus. Scoreur, dans son tournoi. */
export function getEtatBigShootOffSaisie(
  tournoiId: number,
  phaseId: number,
): Promise<EtatBigShootOff> {
  return fetchJson<EtatBigShootOff>(
    `/api/v1/big-shoot-off/saisie/${tournoiId}/${phaseId}`,
    undefined,
    'scoreur',
  )
}

/** Saisit (ou réédite) une volée. `identifiantSaisie` dédoublonne le rejeu (ADR-0036). */
export function saisirVolee(corps: {
  tournoiId: number
  phaseId: number
  archerId: number
  numero: number
  valeurs: string[]
  identifiantSaisie?: string
}): Promise<EtatBigShootOff> {
  return fetchJson<EtatBigShootOff>(
    '/api/v1/big-shoot-off/volees',
    {
      method: 'POST',
      body: JSON.stringify({
        tournoi_id: corps.tournoiId,
        phase_id: corps.phaseId,
        archer_id: corps.archerId,
        numero: corps.numero,
        valeurs: corps.valeurs,
        identifiant_saisie: corps.identifiantSaisie ?? null,
      }),
    },
    'scoreur',
  )
}

/** Valide la manche courante d'un finaliste — c'est elle qui entrera au classement. */
export function validerManche(corps: {
  tournoiId: number
  phaseId: number
  archerId: number
  identifiantSaisie?: string
}): Promise<EtatBigShootOff> {
  return fetchJson<EtatBigShootOff>(
    '/api/v1/big-shoot-off/validations',
    {
      method: 'POST',
      body: JSON.stringify({
        tournoi_id: corps.tournoiId,
        phase_id: corps.phaseId,
        archer_id: corps.archerId,
        identifiant_saisie: corps.identifiantSaisie ?? null,
      }),
    },
    'scoreur',
  )
}
