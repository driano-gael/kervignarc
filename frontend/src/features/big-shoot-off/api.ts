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

/** La photo d'un Big Shoot Off, telle que la salle la lit. */
export interface EtatBigShootOff {
  phase_id: number
  projection: Projection
  tireurs: Tireur[]
  manches: Manche[]
  termine: boolean
  barrage: BarrageEnAttente | null
}

/** Le barrage **en consultation**.
 *
 * ⚠️ **Type distinct, en miroir de `BarragePublicReponse` côté serveur.** Le backend a dédoublé la
 * classe pour qu'un champ ajouté demain au barrage du scoreur ne parte pas au public ; garder ici
 * le type du scoreur rendait la garantie **à sens unique** (relevé par l'axe adversarial) : le
 * champ neuf aurait compilé côté public et rendu `undefined` sur l'écran projeté, le serveur ne le
 * servant pas. Les deux types coïncident aujourd'hui — c'est voulu, pas une duplication à résorber. */
export interface BarragePublic {
  archer_ids: number[]
  noms: string[]
  places: number
}

/** Le finaliste **en consultation** : son sort et ce qu'il a marqué, jamais ce qu'il doit tirer.
 *
 * `prochaine_volee` n'y est pas : c'est une affordance de **saisie** (ADR-0089 §5). Ne pas
 * « compléter » ce type en recopiant `Tireur` — l'absence de ce champ **est** la décision, et un
 * test la verrouille côté serveur.
 *
 * ⚠️ `en_lice` **a quitté le contrat public en revue** : aucune vue publique ne le lisait, et il
 * redit ce que `rang === null` dit déjà — deux champs pour un fait, c'est la porte ouverte à ce
 * qu'ils divergent un jour sans que rien ne le voie. Le compte se dérive de `rang` (`nbEnLice`). */
export type TireurPublic = Omit<Tireur, 'prochaine_volee' | 'en_lice'>

/** La manche **en consultation** : sans la numérotation de volées, qui sert la feuille de saisie. */
export type ManchePublique = Omit<Manche, 'volees'>

/** Le déroulé annoncé du format, tel qu'un spectateur peut le lire : « 12 → 8 → 6 → 5 ».
 *
 * ⚠️ `eliminations` et `manches_jouables` **ont quitté le contrat public en revue** : servis, mais
 * lus par aucune vue. `eliminations` est le réglage d'atelier lui-même, dont `effectif` + `paliers`
 * est la forme lisible.
 *
 * ⚠️ **`restants` n'est PAS le nombre d'archers en lice** : c'est `paliers[-1]`, l'effectif à la
 * **fin** du format — une constante de la phase. Le compte de ceux qui tirent encore se dérive de
 * `tireurs` (`nbEnLice`, dans `publique.ts`). L'avoir confondu a coûté un défaut bloquant en revue. */
export type ProjectionPublique = Omit<
  Projection,
  'volees' | 'fleches_par_volee' | 'manches_ignorees' | 'eliminations' | 'manches_jouables'
>

/** La photo **rédigée** d'un Big Shoot Off — appli publique et écran de salle (E05US031). */
export interface EtatBigShootOffPublic {
  phase_id: number
  projection: ProjectionPublique
  tireurs: TireurPublic[]
  manches: ManchePublique[]
  termine: boolean
  barrage: BarragePublic | null
}

/** L'état **rédigé** — lecture **ouverte et anonyme**, comme `/poules/etat` et `/suisse/etat`. */
export function getEtatBigShootOffPublic(
  tournoiId: number,
  phaseId: number,
): Promise<EtatBigShootOffPublic> {
  return fetchJson<EtatBigShootOffPublic>(
    `/api/v1/big-shoot-off/etat/${tournoiId}/${phaseId}`,
    undefined,
    'aucune',
  )
}

/** L'état **de saisie** : jeton scoreur, et borné au tournoi du scoreur (403 sinon).
 *
 * ⚠️ **La route s'appelait `/etat` jusqu'au 17/08/2026** (E05US031, ADR-0089 §5). Elle a pris le nom
 * que les poules et le suisse donnent à leur lecture de saisie, et rendu `/etat` au public : trois
 * formats jumeaux portaient deux conventions, dont une qui plaçait une lecture protégée derrière le
 * nom de la lecture ouverte. */
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
