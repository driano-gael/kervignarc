// Présentation de l'adjacence des duellistes sur les cibles (E03US009, ADR-0048) — logique pure,
// testée en node (comme les autres `presentation.ts` des features). Le serveur signale au niveau
// **cible** les cas où l'adjacence « adversaires côte à côte » n'est pas garantie, et liste au
// niveau plan les **duels séparés**. Ici on dérive le décompte et le résumé affichés, sans dépendre
// d'un composant. C'est un **avertissement d'organisation** (ambre, DV-03), jamais une erreur :
// l'admin ajuste à la main s'il le souhaite (E03US004).
//
// Jumeau de `placement/presentation.ts` (mixité de club), à une nuance de comptage près : la
// bannière chiffre les **duels séparés** (`duels_separes`), pas les cibles — une cible peut porter
// plusieurs duels, le compte de duels est plus juste pour le message.

import type { CiblePlaceeDuel, PlanDeDuels } from './api'

// Nombre de cibles dont l'adjacence n'est pas garantie (au moins un duel non côte à côte).
export function compterAdjacenceNonGarantie(cibles: CiblePlaceeDuel[]): number {
  return cibles.filter((cible) => cible.adjacence_non_garantie).length
}

// Résumé pour la bannière de l'écran de plan de duels : `null` quand aucun duel n'est séparé (pas de
// bannière), sinon un message **chiffré** au bon accord (1 duel / N duels), sur le modèle des autres
// alertes ambre de l'écran. Le compte porte sur `duels_separes` (nombre de duels), plus juste que le
// nombre de cibles signalées.
export function resumeAdjacenceNonGarantie(plan: PlanDeDuels): string | null {
  const nombre = plan.duels_separes.length
  if (nombre === 0) return null
  const pluriel = nombre > 1
  return `${nombre} duel${pluriel ? 's ne sont' : ' n’est'} pas placé${pluriel ? 's' : ''} côte à côte (adversaires séparés).`
}
