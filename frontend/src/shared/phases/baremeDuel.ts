// Le **barème des duels** d'une étape (E01US011, ADR-0117) : un barème par défaut, des surcharges
// par arme, et un barème des derniers tours (E01US027). Logique pure, partagée par « Phases » et
// « Composer un format ».

import type { TypePhase } from './catalogue'

export type ModeDuel = 'sets' | 'cumul'

export interface BaremeDuel {
  mode: ModeDuel
  nb_manches: number
  nb_fleches_par_volee: number
  points_pour_gagner: number
  /** Flèches de barrage par camp : 1 en individuel, 1 par archer en équipe (§8.2, E13US003). */
  nb_fleches_barrage: number
}

export interface SurchargeArme {
  arme: string
  bareme: BaremeDuel
}

export interface BaremeDesDerniersTours {
  nb_tours: number
  par_defaut: BaremeDuel
  surcharges: SurchargeArme[]
}

export interface ReglageBaremeDuel {
  par_defaut: BaremeDuel
  surcharges: SurchargeArme[]
  derniers_tours: BaremeDesDerniersTours | null
}

export interface EtatBareme {
  mode: ModeDuel
  manches: string
  fleches: string
  points: string
  barrage: string
}

export interface EtatSurcharge {
  arme: string
  bareme: EtatBareme
}

export interface EtatDerniersTours {
  tours: string
  par_defaut: EtatBareme
  surcharges: EtatSurcharge[]
}

export interface EtatBaremeDuel {
  /** `false` = aucun réglage : le serveur applique son défaut FFTA (CA 3). */
  regle: boolean
  par_defaut: EtatBareme
  surcharges: EtatSurcharge[]
  /** `null` = un seul barème pour toute la phase (E01US027). */
  derniers: EtatDerniersTours | null
}

// Miroir de `domain/contrat_phase.py::TYPES_A_BAREME_DE_DUEL` — le serveur refuse les autres (422).
export const TYPES_A_BAREME_DE_DUEL: ReadonlySet<TypePhase> = new Set<TypePhase>([
  'elimination_directe',
  'poules',
  'suisse',
  'colline',
])

export const MANCHES_MAX = 64
export const FLECHES_MAX = 12
// Même borne que `BaremeDesDerniersToursDTO.nb_tours` (api/v1/phases.py).
export const DERNIERS_TOURS_MAX = 16

const SETS_FFTA: BaremeDuel = {
  mode: 'sets',
  nb_manches: 5,
  nb_fleches_par_volee: 3,
  points_pour_gagner: 6,
  nb_fleches_barrage: 1,
}
const SETS_CLUB: BaremeDuel = { ...SETS_FFTA, points_pour_gagner: 4 }
const CUMUL_POULIES: BaremeDuel = {
  mode: 'cumul',
  nb_manches: 5,
  nb_fleches_par_volee: 3,
  points_pour_gagner: 0,
  nb_fleches_barrage: 1,
}
// Équipe (§6.4, §7, §8.2) : 4 manches, 2 flèches par archer, barrage d'1 flèche par archer.
const SETS_EQUIPE: BaremeDuel = {
  mode: 'sets',
  nb_manches: 4,
  nb_fleches_par_volee: 6,
  points_pour_gagner: 5,
  nb_fleches_barrage: 3,
}
const CUMUL_EQUIPE: BaremeDuel = { ...SETS_EQUIPE, mode: 'cumul', points_pour_gagner: 0 }
const SETS_MIXTE: BaremeDuel = { ...SETS_EQUIPE, nb_fleches_par_volee: 4, nb_fleches_barrage: 2 }
const CUMUL_MIXTE: BaremeDuel = { ...SETS_MIXTE, mode: 'cumul', points_pour_gagner: 0 }

export function depuisBareme(bareme: BaremeDuel): EtatBareme {
  return {
    mode: bareme.mode,
    manches: String(bareme.nb_manches),
    fleches: String(bareme.nb_fleches_par_volee),
    points: String(bareme.points_pour_gagner),
    barrage: String(bareme.nb_fleches_barrage),
  }
}

export const BAREME_DUEL_NON_REGLE: EtatBaremeDuel = {
  regle: false,
  par_defaut: depuisBareme(SETS_FFTA),
  surcharges: [],
  derniers: null,
}

function depuisSurcharges(surcharges: readonly SurchargeArme[]): EtatSurcharge[] {
  return surcharges.map((s) => ({ arme: s.arme, bareme: depuisBareme(s.bareme) }))
}

export function depuisReglage(reglage: ReglageBaremeDuel | null): EtatBaremeDuel {
  if (reglage === null) return BAREME_DUEL_NON_REGLE
  const fin = reglage.derniers_tours
  return {
    regle: true,
    par_defaut: depuisBareme(reglage.par_defaut),
    surcharges: depuisSurcharges(reglage.surcharges),
    derniers:
      fin === null
        ? null
        : {
            tours: String(fin.nb_tours),
            par_defaut: depuisBareme(fin.par_defaut),
            surcharges: depuisSurcharges(fin.surcharges),
          },
  }
}

function entier(texte: string, min: number, max: number): number | undefined {
  const nombre = Number(texte)
  if (texte.trim() === '' || !Number.isInteger(nombre) || nombre < min || nombre > max) {
    return undefined
  }
  return nombre
}

export function versBareme(etat: EtatBareme): BaremeDuel | undefined {
  const manches = entier(etat.manches, 1, MANCHES_MAX)
  const fleches = entier(etat.fleches, 1, FLECHES_MAX)
  const barrage = entier(etat.barrage, 1, FLECHES_MAX)
  if (manches === undefined || fleches === undefined || barrage === undefined) return undefined
  if (etat.mode === 'cumul') {
    return {
      mode: 'cumul',
      nb_manches: manches,
      nb_fleches_par_volee: fleches,
      points_pour_gagner: 0,
      nb_fleches_barrage: barrage,
    }
  }
  // Même borne que `BaremeDuel.__post_init__` : le seuil doit être atteignable en `manches` sets.
  const points = entier(etat.points, 1, 2 * manches)
  if (points === undefined) return undefined
  return {
    mode: 'sets',
    nb_manches: manches,
    nb_fleches_par_volee: fleches,
    points_pour_gagner: points,
    nb_fleches_barrage: barrage,
  }
}

export function cleArme(arme: string): string {
  return arme.trim().toLocaleLowerCase('fr')
}

function versSurcharges(etats: readonly EtatSurcharge[]): SurchargeArme[] | undefined {
  const vues = new Set<string>()
  const surcharges: SurchargeArme[] = []
  for (const brute of etats) {
    const bareme = versBareme(brute.bareme)
    const cle = cleArme(brute.arme)
    if (bareme === undefined || cle === '' || vues.has(cle)) return undefined
    vues.add(cle)
    surcharges.push({ arme: brute.arme.trim(), bareme })
  }
  return surcharges
}

function versDerniersTours(
  etat: EtatDerniersTours | null,
): BaremeDesDerniersTours | null | undefined {
  if (etat === null) return null
  const nb_tours = entier(etat.tours, 1, DERNIERS_TOURS_MAX)
  const par_defaut = versBareme(etat.par_defaut)
  const surcharges = versSurcharges(etat.surcharges)
  if (nb_tours === undefined || par_defaut === undefined || surcharges === undefined) {
    return undefined
  }
  return { nb_tours, par_defaut, surcharges }
}

/** `null` = non réglé ; `undefined` = saisie invalide, à ne pas envoyer. */
export function versReglage(etat: EtatBaremeDuel): ReglageBaremeDuel | null | undefined {
  if (!etat.regle) return null
  const par_defaut = versBareme(etat.par_defaut)
  const surcharges = versSurcharges(etat.surcharges)
  const derniers_tours = versDerniersTours(etat.derniers)
  if (par_defaut === undefined || surcharges === undefined || derniers_tours === undefined) {
    return undefined
  }
  return { par_defaut, surcharges, derniers_tours }
}

export function estValide(etat: EtatBaremeDuel): boolean {
  return versReglage(etat) !== undefined
}

// DETTE-119 — miroir de `domain/duel.py::_est_poulies` (presets, écarts), sans test commun.
export function estPoulies(arme: string): boolean {
  const normalise = arme.trim().toLocaleLowerCase('fr')
  return normalise.includes('poulie') || normalise.includes('compound')
}

export function armesDistinctes(armes: readonly (string | null)[]): string[] {
  const retenues = new Map<string, string>()
  for (const arme of armes) {
    if (arme === null || arme.trim() === '') continue
    if (!retenues.has(cleArme(arme))) retenues.set(cleArme(arme), arme.trim())
  }
  return [...retenues.values()].sort((a, b) => a.localeCompare(b, 'fr'))
}

function surchargesPoulies(armes: readonly string[], poulies: BaremeDuel): EtatSurcharge[] {
  return armesDistinctes(armes)
    .filter(estPoulies)
    .map((arme) => ({ arme, bareme: depuisBareme(poulies) }))
}

function preset(defaut: BaremeDuel, armes: readonly string[], poulies: BaremeDuel): EtatBaremeDuel {
  return {
    regle: true,
    par_defaut: depuisBareme(defaut),
    surcharges: surchargesPoulies(armes, poulies),
    derniers: null,
  }
}

export function presetFfta(armes: readonly string[]): EtatBaremeDuel {
  return preset(SETS_FFTA, armes, CUMUL_POULIES)
}

// DETTE-119 — recopiés au domaine (`BaremeDuel.preset_ffta_equipe`), défaut d'une phase d'équipes.
export function presetFftaEquipe(armes: readonly string[]): EtatBaremeDuel {
  return preset(SETS_EQUIPE, armes, CUMUL_EQUIPE)
}

export function presetFftaMixte(armes: readonly string[]): EtatBaremeDuel {
  return preset(SETS_MIXTE, armes, CUMUL_MIXTE)
}

/** Référentiel §10.1 : premier à 4, puis à 6 dès les ½ finales — poulies au cumul partout. */
export function presetClub(armes: readonly string[]): EtatBaremeDuel {
  return {
    ...preset(SETS_CLUB, armes, CUMUL_POULIES),
    derniers: {
      tours: '2',
      par_defaut: depuisBareme(SETS_FFTA),
      surcharges: surchargesPoulies(armes, CUMUL_POULIES),
    },
  }
}

/** Ce que pose la case « derniers tours » une fois cochée : le barème principal recopié, K = 2. */
export function derniersToursDepuis(etat: EtatBaremeDuel): EtatDerniersTours {
  return {
    tours: '2',
    par_defaut: { ...etat.par_defaut },
    surcharges: etat.surcharges.map((s) => ({ arme: s.arme, bareme: { ...s.bareme } })),
  }
}

/** Les K derniers tours, dits dans le vocabulaire du format (E01US027, CA 3). */
// DETTE-020 — 3ᵉ domicile du compte « à rebours de la finale » : un libellé de réglage, sans
// tableau à interroger.
export function libelleDerniersTours(nb: number, type: TypePhase): string {
  if (type === 'elimination_directe') {
    if (nb === 1) return 'la finale'
    if (nb === 2) return 'les ½ finales et la finale'
    if (nb === 3) return 'les ¼ de finale, les ½ finales et la finale'
    return `les ${nb} derniers tours`
  }
  if (type === 'suisse') return nb === 1 ? 'la dernière ronde' : `les ${nb} dernières rondes`
  if (type === 'colline') return nb === 1 ? 'la dernière manche' : `les ${nb} dernières manches`
  return nb === 1 ? 'le dernier tour' : `les ${nb} derniers tours`
}

export interface EcartsDArmes {
  /** Armes à poulies du tournoi qu'aucune surcharge ne désigne : elles tireraient en sets. */
  poulieSansSurcharge: string[]
  /** Surcharges dont l'arme n'existe dans aucune catégorie connue : elles ne servent à rien. */
  surchargeOrpheline: string[]
}

/** Ce que le réglage ne couvre pas, face aux armes connues (ADR-0117, Conséquences). */
/** Les armes connues, ou pourquoi on ne les connaît pas : on ne pose pas de preset à l'aveugle. */
export type ArmesConnues = readonly string[] | 'chargement' | 'erreur'

export function ecartsDArmes(etat: EtatBaremeDuel, armes: readonly string[]): EcartsDArmes {
  if (!etat.regle) return { poulieSansSurcharge: [], surchargeOrpheline: [] }
  // Les deux barèmes se jugent pareil (E01US027) : une arme oubliée dans l'un est un écart.
  const portees = etat.derniers === null ? [etat] : [etat, etat.derniers]
  const connues = new Set(armes.map(cleArme))
  return {
    poulieSansSurcharge: armesDistinctes(
      portees.flatMap((portee) => {
        // Un défaut déjà au cumul couvre les poulies : il n'y a pas d'écart à signaler.
        if (portee.par_defaut.mode === 'cumul') return []
        const surchargees = new Set(portee.surcharges.map((s) => cleArme(s.arme)))
        return armes.filter((arme) => estPoulies(arme) && !surchargees.has(cleArme(arme)))
      }),
    ),
    surchargeOrpheline: armesDistinctes(
      portees.flatMap((portee) =>
        portee.surcharges
          .map((s) => s.arme.trim())
          .filter((arme) => arme !== '' && !connues.has(cleArme(arme))),
      ),
    ),
  }
}
