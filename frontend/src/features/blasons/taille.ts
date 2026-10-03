// Taille d'un blason proposée en fractions (E00US016). Le serveur garde un réel dans `]0, 1]`
// (`domain.blason`) : la déroulante n'est qu'une façon de le saisir.

// Clé d'option = le dénominateur : stable, lisible, et sans flottant dans une `value` de `<select>`.
export const FRACTIONS = [
  { cle: '1', valeur: 1, symbole: '1', libelle: 'Cible entière (1)' },
  { cle: '2', valeur: 1 / 2, symbole: '½', libelle: 'Demi (½)' },
  { cle: '3', valeur: 1 / 3, symbole: '⅓', libelle: 'Tiers (⅓)' },
  { cle: '4', valeur: 1 / 4, symbole: '¼', libelle: 'Quart (¼)' },
] as const

export const AUTRE = 'autre'

// ⚠️ Un tiers ne tombe pas juste en binaire : comparer par `===` rangerait « ⅓ » sous « Autre… »
// dès qu'un client l'aurait arrondi autrement.
const TOLERANCE = 1e-6

const fractionDe = (taille: number) =>
  FRACTIONS.find((fraction) => Math.abs(fraction.valeur - taille) < TOLERANCE)

export function choixDeTaille(taille: number): string {
  return fractionDe(taille)?.cle ?? AUTRE
}

// `null` = saisie à refuser avant envoi ; le serveur reste l'autorité sur les bornes.
export function tailleDuChoix(choix: string, saisieLibre: string): number | null {
  const fraction = FRACTIONS.find((candidate) => candidate.cle === choix)
  if (fraction) return fraction.valeur
  const texte = saisieLibre.trim().replace(',', '.')
  if (texte === '') return null
  const valeur = Number(texte)
  return Number.isFinite(valeur) && valeur > 0 && valeur <= 1 ? valeur : null
}

export function libelleTaille(taille: number): string {
  return fractionDe(taille)?.symbole ?? taille.toLocaleString('fr-FR')
}
