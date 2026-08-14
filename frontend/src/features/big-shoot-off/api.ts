// Accès HTTP du **Big Shoot Off** (E05US028) — miroir des DTO de `api/v1/big_shoot_off.py`.
//
// ⚠️ **Les écritures vivent ici**, contrairement aux poules. Une rencontre de poule *est* un duel
// ordinaire, donc elle s'écrit par les hooks de `features/saisie-duels` (ADR-0083 §7) ; une volée de
// Big Shoot Off est **collective** et n'a pas d'adversaire — le pavé de duel ne s'y applique pas, et
// il n'existe aucun hook de tir de série côté scoreur à emprunter. Ce sont donc deux mutations
// propres à cette feature.
//
// Les deux écritures rendent l'**état complet** plutôt que l'objet écrit : une manche validée peut
// éliminer, donc changer la lice de tout le monde. Rendre la volée seule obligerait la tablette à
// relire aussitôt et laisserait une fenêtre où l'écran montre un archer sorti comme encore en lice.

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

/** La photo d'un Big Shoot Off, telle que la salle la lit. */
export interface EtatBigShootOff {
  phase_id: number
  projection: Projection
  tireurs: Tireur[]
  manches: Manche[]
  termine: boolean
  barrage: BarrageEnAttente | null
}

export function getEtatBigShootOff(tournoiId: number, phaseId: number): Promise<EtatBigShootOff> {
  return fetchJson<EtatBigShootOff>(
    `/api/v1/big-shoot-off/etat/${tournoiId}/${phaseId}`,
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
