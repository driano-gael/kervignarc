// Le **barème des duels** d'une étape (E01US011, ADR-0117) : un barème par défaut et des surcharges
// par arme. Logique pure, partagée par « Phases » et « Composer un format ».

import type { TypePhase } from './catalogue'

export type ModeDuel = 'sets' | 'cumul'

export interface BaremeDuel {
  mode: ModeDuel
  nb_manches: number
  nb_fleches_par_volee: number
  points_pour_gagner: number
}

export interface SurchargeArme {
  arme: string
  bareme: BaremeDuel
}

export interface ReglageBaremeDuel {
  par_defaut: BaremeDuel
  surcharges: SurchargeArme[]
}

export interface EtatBareme {
  mode: ModeDuel
  manches: string
  fleches: string
  points: string
}

export interface EtatBaremeDuel {
  /** `false` = aucun réglage : le serveur applique son défaut FFTA (CA 3). */
  regle: boolean
  par_defaut: EtatBareme
  surcharges: { arme: string; bareme: EtatBareme }[]
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

const SETS_FFTA: BaremeDuel = {
  mode: 'sets',
  nb_manches: 5,
  nb_fleches_par_volee: 3,
  points_pour_gagner: 6,
}
const SETS_CLUB: BaremeDuel = { ...SETS_FFTA, points_pour_gagner: 4 }
const CUMUL_POULIES: BaremeDuel = {
  mode: 'cumul',
  nb_manches: 5,
  nb_fleches_par_volee: 3,
  points_pour_gagner: 0,
}

export function depuisBareme(bareme: BaremeDuel): EtatBareme {
  return {
    mode: bareme.mode,
    manches: String(bareme.nb_manches),
    fleches: String(bareme.nb_fleches_par_volee),
    points: String(bareme.points_pour_gagner),
  }
}

export const BAREME_DUEL_NON_REGLE: EtatBaremeDuel = {
  regle: false,
  par_defaut: depuisBareme(SETS_FFTA),
  surcharges: [],
}

export function depuisReglage(reglage: ReglageBaremeDuel | null): EtatBaremeDuel {
  if (reglage === null) return BAREME_DUEL_NON_REGLE
  return {
    regle: true,
    par_defaut: depuisBareme(reglage.par_defaut),
    surcharges: reglage.surcharges.map((s) => ({ arme: s.arme, bareme: depuisBareme(s.bareme) })),
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
  if (manches === undefined || fleches === undefined) return undefined
  if (etat.mode === 'cumul') {
    return {
      mode: 'cumul',
      nb_manches: manches,
      nb_fleches_par_volee: fleches,
      points_pour_gagner: 0,
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
  }
}

export function cleArme(arme: string): string {
  return arme.trim().toLocaleLowerCase('fr')
}

/** `null` = non réglé ; `undefined` = saisie invalide, à ne pas envoyer. */
export function versReglage(etat: EtatBaremeDuel): ReglageBaremeDuel | null | undefined {
  if (!etat.regle) return null
  const par_defaut = versBareme(etat.par_defaut)
  if (par_defaut === undefined) return undefined
  const vues = new Set<string>()
  const surcharges: SurchargeArme[] = []
  for (const brute of etat.surcharges) {
    const bareme = versBareme(brute.bareme)
    const cle = cleArme(brute.arme)
    if (bareme === undefined || cle === '' || vues.has(cle)) return undefined
    vues.add(cle)
    surcharges.push({ arme: brute.arme.trim(), bareme })
  }
  return { par_defaut, surcharges }
}

export function estValide(etat: EtatBaremeDuel): boolean {
  return versReglage(etat) !== undefined
}

// Miroir de `domain/duel.py::_est_poulies` — sert **seulement** à pré-remplir un preset (ADR-0117).
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

function preset(defaut: BaremeDuel, armes: readonly string[]): EtatBaremeDuel {
  return {
    regle: true,
    par_defaut: depuisBareme(defaut),
    surcharges: armesDistinctes(armes)
      .filter(estPoulies)
      .map((arme) => ({ arme, bareme: depuisBareme(CUMUL_POULIES) })),
  }
}

export function presetFfta(armes: readonly string[]): EtatBaremeDuel {
  return preset(SETS_FFTA, armes)
}

export function presetClub(armes: readonly string[]): EtatBaremeDuel {
  return preset(SETS_CLUB, armes)
}
