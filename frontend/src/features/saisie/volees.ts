// Logique pure de la saisie (E04US002) — points, volée à saisir, libellé de grain.
//
// Isolée du rendu React pour être **testée** (vitest tourne en environnement node, sans DOM). Le
// serveur reste l'**autorité** (barème, zones, cumul officiel) : ces fonctions ne servent qu'à
// piloter l'affichage — total provisoire d'une volée en cours, quelle volée saisir, etc.

import type { Grain, Volee } from './api'

// Points d'une valeur de zone. `M` (manqué) = 0 ; les autres sont numériques (« 10 » → 10). Pas de
// « X » dans le vocabulaire FFTA retenu (cf. `domain/blason.ZoneScore`). Une valeur inattendue → 0
// (défensif : le pavé ne propose que des zones légales, mais on ne fait pas confiance à l'affichage).
export function pointsZone(valeur: string): number {
  if (valeur === 'M') return 0
  const points = Number.parseInt(valeur, 10)
  return Number.isNaN(points) ? 0 : points
}

// Total provisoire d'une volée en cours de frappe (avant enregistrement). Le cumul **officiel** de
// la série vient du serveur (volées validées uniquement) ; ceci n'est qu'un retour visuel immédiat.
export function totalVolee(valeurs: readonly string[]): number {
  return valeurs.reduce((somme, valeur) => somme + pointsZone(valeur), 0)
}

// La prochaine volée à saisir : la **plus petite** (1..nbVolees) pas encore **saisie**. Une volée
// est « faite » dès qu'elle est persistée — la **validation** (le verrou) est l'acte du scoreur, plus
// tard : le marqueur avance sans l'attendre. Si toutes sont saisies, on reste sur la **dernière**
// (l'édition d'une volée déjà saisie passe par le navigateur de volées, tant qu'elle n'est pas
// verrouillée — CA « édition avant validation »).
export function prochaineASaisir(volees: readonly Volee[], nbVolees: number): number {
  for (let numero = 1; numero <= nbVolees; numero += 1) {
    if (!volees.some((v) => v.numero === numero)) return numero
  }
  return nbVolees
}

// La volée déjà saisie portant ce numéro (pour pré-remplir le pavé lors d'une réédition), ou `null`.
export function voleeExistante(volees: readonly Volee[], numero: number): Volee | null {
  return volees.find((v) => v.numero === numero) ?? null
}

// Libellé du grain de validation affiché au marqueur (D-11) : il dit **quand** le scoreur viendra.
export function libelleGrain(grain: Grain | null): string {
  if (grain === null) return 'Grain de validation non défini'
  switch (grain.grain) {
    case 'fin_de_serie':
      return 'Validation à la fin de la série'
    case 'fin_de_duel':
      return 'Validation à la fin du duel'
    case 'toutes_les_n_volees':
      return `Validation toutes les ${grain.n_volees ?? '?'} volées`
  }
}
