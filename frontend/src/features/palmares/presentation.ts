// Mise en mots du palmarès (E06US004) — fonctions **pures**, testées à part de React.
//
// Trois règles, non cosmétiques. **Aucun rang inventé** : une fourchette s'affiche « 5ᵉ-8ᵉ » telle
// quelle, choisir un chiffre ferait dire à l'écran ce que la compétition n'a pas décidé (ADR-0065).
// **L'origine se dit** : « 9ᵉ » est ambigu, le préciser (« qualification ») évite de laisser croire
// à une élimination en duel. **Ce qui n'est pas décidé se nomme** : un podium vide dit « en cours
// », un blanc passerait pour une panne d'affichage sur un écran projeté.

import type { LignePalmares, Podium } from './api'

const MEDAILLES: Record<number, string> = { 1: 'Or', 2: 'Argent', 3: 'Bronze' }

// « 3ᵉ », « 5ᵉ-8ᵉ » ou « — » (hors classement). L'exposant ordinal suit l'usage français : « 1ᵉʳ »
// au premier rang, « ᵉ » ensuite.
export function rang(minimum: number | null, maximum: number | null): string {
  if (minimum === null || maximum === null) return '—'
  if (minimum === maximum) return ordinal(minimum)
  // Les **deux** bornes passent par `ordinal` : « 1ᵉ-2ᵉ » au lieu de « 1ᵉʳ-2ᵉ » était
  // le cas le plus visible du palmarès (les deux finalistes, en tête de liste), et le
  // test ne couvrait que `rang(5, 8)` — la seule fourchette dont la borne basse n'est
  // pas 1. Relevé par trois axes de revue.
  return `${ordinal(minimum)}-${ordinal(maximum)}`
}

export function ordinal(valeur: number): string {
  return valeur === 1 ? '1ᵉʳ' : `${valeur}ᵉ`
}

// La médaille d'un rang de podium — vide au-delà du bronze : ces places figurent au podium (la
// petite finale a décerné la 4ᵉ) mais ne reçoivent rien.
export function medaille(rangDansLaPortee: number | null): string {
  return rangDansLaPortee === null ? '' : (MEDAILLES[rangDansLaPortee] ?? '')
}

// La **provenance** d'une place de podium. Le moteur ne monte qu'un seul tableau scratch, donc dans
// la plupart des catégories le bronze est rangé par la qualification faute d'un match qui départage.
// On l'affiche (l'amputer laissait la majorité des catégories sans médailles) mais on le **dit** :
// c'est la distinction entre le classement et le podium, rendue visible plutôt que tranchée en
// supprimant des lignes.
export function provenance(ligne: LignePalmares): string | null {
  return ligne.decerne ? null : 'au classement'
}

// Ce qu'on écrit sous le rang d'une ligne. `null` quand il n'y a rien à ajouter : le cas normal
// d'un rang décerné en duel, où répéter « duels » serait du bruit sur 120 lignes.
export function detail(ligne: LignePalmares): string | null {
  if (ligne.statut === 'disqualifie') return 'Disqualifié'
  if (ligne.statut === 'abandon') return 'Abandon'
  if (ligne.origine === 'qualification') return 'Qualification'
  // ⚠️ « Reste à tirer » et non « à départager » : *départager* est le vocabulaire du
  // **barrage** (E06US003). Dire « à départager » à deux finalistes annonce au public
  // qu'une règle va décider, alors que c'est la finale — et c'est l'inverse pour les
  // quatre battus 5ᵉ-8ᵉ, que plus aucun match ne séparera. Les deux se présentaient
  // sous le même libellé faute d'exposer `en_lice` (relevé en revue, trois axes).
  if (ligne.en_lice) return 'Reste à tirer'
  if (ligne.rang_min !== ligne.rang_max) return 'Ex æquo'
  if (!ligne.decerne) return 'Départagé au classement'
  return null
}

// L'état d'un bloc de podium quand il n'est pas complet.
//
// ⚠️ **`enAttente` distingue « pas encore » de « jamais »** (E16US014) : un bloc peut n'avoir aucune
// place parce que les finales restent à tirer, ou parce qu'aucun de ses archers n'a disputé de duel
// — cas devenu **typique** avec la portée club, où la plupart des clubs n'ont personne au tableau
// (`DETTE-028`). Annoncer « les finales ne sont pas toutes tirées » y serait faux deux fois : il n'y
// a ni finale de club, ni finale restante.
export function etatPodium(podium: Podium, profondeur: number): string | null {
  if (podium.places.length === 0) {
    return podium.en_attente
      ? 'Podium en cours — aucune place décernée.'
      : 'Aucune place départageable — ces archers sont ex æquo.'
  }
  // Comparé à l'**effectif du groupe**, pas à la constante 3 : un groupe de deux archers (courant
  // en salle — Benjamine, Cadet Femme…) a un podium complet à deux noms, et affichait « podium
  // partiel » à perpétuité, tournoi terminé compris (relevé en revue, axes B et C1).
  //
  // ⚠️ `profondeur` entre au minimum **sans remplacer le 3** (E16US014) : le seuil reste celui des
  // **médailles**, pas des places affichées — sinon le réglage par défaut (4 places) ferait dire
  // « partiel » à tout podium complet de trois médaillés, une régression sur tous les tournois.
  const complet = Math.min(3, profondeur, podium.effectif)
  if (podium.places.length < complet) {
    return podium.en_attente
      ? 'Podium partiel — les finales ne sont pas toutes tirées.'
      : 'Podium partiel — les places restantes sont ex æquo.'
  }
  return null
}

export const nomComplet = (ligne: LignePalmares) => `${ligne.prenom} ${ligne.nom}`.trim()
