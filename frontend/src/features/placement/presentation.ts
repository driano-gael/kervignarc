// Présentation de la mixité des clubs sur les cibles (E03US006, RG-3) — logique pure, testée en
// node (comme les autres `presentation.ts` des features). Le serveur signale au niveau **cible**
// les cas où la mixité « ≥ 2 clubs par cible » n'est pas garantie (un seul club, ou club inconnu —
// *indécidable*, ADR-0014) ; ici on dérive le décompte et le résumé affichés, sans dépendre d'un
// composant. C'est un **avertissement d'équité** (ambre, DV-03), jamais une erreur : l'admin ajuste
// à la main s'il le souhaite (E03US004).

import type { CiblePlacee, Cloisonnement } from './api'

// Nombre de cibles dont la mixité de club n'est pas garantie (≥ 2 archers, < 2 clubs connus).
export function compterMixiteNonGarantie(cibles: CiblePlacee[]): number {
  return cibles.filter((cible) => cible.mixite_non_garantie).length
}

// Résumé pour la bannière de l'écran de placement : `null` quand tout va bien (pas de bannière),
// sinon un message **chiffré** au bon accord (1 cible / N cibles), sur le modèle des autres alertes
// ambre de l'écran.
export function resumeMixiteNonGarantie(cibles: CiblePlacee[]): string | null {
  const nombre = compterMixiteNonGarantie(cibles)
  if (nombre === 0) return null
  const pluriel = nombre > 1
  return `${nombre} cible${pluriel ? 's' : ''} sans mixité de club garantie (un seul club, ou club inconnu).`
}

// --- Cloisonnement des cibles (E03US007) --------------------------------------------------------

// Libellé du réglage à quatre positions, pour le sélecteur **et** pour la bannière : une seule
// source, pour que l'écran ne puisse pas dire « par catégorie » à un endroit et « catégories » à un
// autre. Ordre du plus permissif au plus strict, comme l'énumération du domaine.
export const LIBELLE_CLOISONNEMENT: Record<Cloisonnement, string> = {
  aucun: 'Aucun cloisonnement',
  categorie: 'Une seule catégorie par cible',
  blason: 'Un seul blason par cible',
  blason_et_categorie: 'Un seul blason et une seule catégorie par cible',
}

// Résumé de la bannière : `null` quand aucune cible ne viole le réglage (rien à dire). Sinon un
// message **chiffré** qui dit aussi **quoi faire** — ces cibles viennent forcément d'un plan posé
// avant l'activation du réglage, et c'est la régénération qui les remet d'aplomb.
export function resumeCloisonnementNonRespecte(cibles: CiblePlacee[]): string | null {
  const nombre = cibles.filter((cible) => cible.cloisonnement_non_respecte).length
  if (nombre === 0) return null
  const pluriel = nombre > 1
  return (
    `${nombre} cible${pluriel ? 's' : ''} ne respecte${pluriel ? 'nt' : ''} pas le cloisonnement ` +
    `demandé (plan posé avant le réglage) : régénérez le plan ou déplacez les archers concernés.`
  )
}
