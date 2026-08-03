// Mise en mots du palmarès (E06US004) — fonctions **pures**, testées à part de React.
//
// Trois règles, et elles ne sont pas cosmétiques :
//
// 1. **Aucun rang inventé.** Une fourchette s'affiche « 5ᵉ-8ᵉ » telle quelle. Choisir un chiffre
//    ferait dire à l'écran ce que la compétition n'a pas décidé — c'est le parti d'ADR-0065, repris
//    ici (E07US008 le tenait déjà pour le routage).
// 2. **L'origine se dit.** « 9ᵉ » est ambigu : le préciser (« qualification ») évite de laisser
//    croire à une élimination en duel à quelqu'un qui n'a jamais tiré de duel.
// 3. **Ce qui n'est pas décidé se nomme.** Un podium vide dit « en cours », pas rien — un blanc
//    passerait pour une panne d'affichage sur un écran projeté.

import type { LignePalmares, PodiumCategorie } from './api'

const MEDAILLES: Record<number, string> = { 1: 'Or', 2: 'Argent', 3: 'Bronze' }

// « 3ᵉ », « 5ᵉ-8ᵉ » ou « — » (hors classement). L'exposant ordinal suit l'usage français : « 1ᵉʳ »
// au premier rang, « ᵉ » ensuite.
export function rang(minimum: number | null, maximum: number | null): string {
  if (minimum === null || maximum === null) return '—'
  if (minimum === maximum) return ordinal(minimum)
  return `${minimum}ᵉ-${ordinal(maximum)}`
}

export function ordinal(valeur: number): string {
  return valeur === 1 ? '1ᵉʳ' : `${valeur}ᵉ`
}

// La médaille d'un rang de podium — vide au 4ᵉ, qui figure au podium (la petite finale l'a décerné)
// mais ne reçoit rien.
export function medaille(rangCategorie: number | null): string {
  return rangCategorie === null ? '' : (MEDAILLES[rangCategorie] ?? '')
}

// Ce qu'on écrit sous le rang d'une ligne. `null` quand il n'y a rien à ajouter : le cas normal
// d'un rang décerné en duel, où répéter « duels » serait du bruit sur 120 lignes.
export function detail(ligne: LignePalmares): string | null {
  if (ligne.statut === 'disqualifie') return 'Disqualifié'
  if (ligne.statut === 'abandon') return 'Abandon'
  if (ligne.origine === 'qualification') return 'Qualification'
  if (ligne.rang_min !== ligne.rang_max) return 'À départager'
  return null
}

// Le titre d'un bloc de podium, et son état quand il est vide.
export function etatPodium(podium: PodiumCategorie): string | null {
  if (podium.lignes.length === 0) return 'Podium en cours — aucune place décernée.'
  if (podium.lignes.length < 3) return 'Podium partiel — les finales ne sont pas toutes tirées.'
  return null
}

export const nomComplet = (ligne: LignePalmares) => `${ligne.prenom} ${ligne.nom}`.trim()
