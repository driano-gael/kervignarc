// Présentation de la mixité des clubs sur les cibles (E03US006, RG-3) — logique pure, testée en
// node (comme les autres `presentation.ts` des features). Le serveur signale au niveau **cible**
// les cas où la mixité « ≥ 2 clubs par cible » n'est pas garantie (un seul club, ou club inconnu —
// *indécidable*, ADR-0014) ; ici on dérive le décompte et le résumé affichés, sans dépendre d'un
// composant. C'est un **avertissement d'équité** (ambre, DV-03), jamais une erreur : l'admin ajuste
// à la main s'il le souhaite (E03US004).

import type { CiblePlacee } from './api'

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
