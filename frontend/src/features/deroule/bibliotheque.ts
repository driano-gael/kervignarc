// Ce que l'atelier tire de la bibliothèque du club (E01US024, E01US011) — logique pure, aucun React.

import { armesDistinctes, type ArmesConnues } from '../../shared/phases/baremeDuel'
import type { FormatTournoi } from '../patrimoine/api'

// À défaut de choix explicite, le premier de la bibliothèque ouvre l'écran : arriver sur une page
// vide alors que le club a des formats donnerait à croire qu'il n'y en a aucun.
export function formatChoisi(
  formats: readonly FormatTournoi[] | undefined,
  choix: number | null,
): FormatTournoi | null {
  return formats?.find((format) => format.id === choix) ?? formats?.[0] ?? null
}

// E01US011 : hors tournoi, ce sont les armes des catégories de bibliothèque qui pré-remplissent.
export function armesDeLaBibliotheque(
  enErreur: boolean,
  categories: readonly { arme: string | null }[] | undefined,
): ArmesConnues {
  if (enErreur) return 'erreur'
  if (categories === undefined) return 'chargement'
  return armesDistinctes(categories.map((categorie) => categorie.arme))
}
