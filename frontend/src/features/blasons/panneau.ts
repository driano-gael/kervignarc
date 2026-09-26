// L'écran des blasons en « liste + panneau latéral » (A06, variante B retenue le 04/08) — E17US007.
// Logique pure : quels groupes afficher, et quel blason le panneau édite.

import type { Blason } from './api'
import type { OrigineBrique } from '../patrimoine/api'

export interface GroupeDeBlasons {
  origine: OrigineBrique
  libelle: string
  blasons: Blason[]
}

// ⚠️ « Référentiel FFTA », jamais « officiels » : l'origine dit d'où vient la brique, **pas** sa
// conformité au règlement (ADR-0060 §4). Un blason FFTA ajusté reste « FFTA » par sa provenance.
const LIBELLE: Record<OrigineBrique, string> = {
  ffta: 'Référentiel FFTA',
  utilisateur: 'Créés par l’organisation',
}

const ORDRE: readonly OrigineBrique[] = ['ffta', 'utilisateur']

// La réserve d'A06 : « séparer visuellement les unités officielles FFTA de celles créées par
// l'admin ». Le référentiel d'abord ; un groupe vide n'est pas rendu.
export function groupesParOrigine(blasons: readonly Blason[]): GroupeDeBlasons[] {
  return ORDRE.map((origine) => ({
    origine,
    libelle: LIBELLE[origine],
    blasons: blasons.filter((b) => b.origine === origine),
  })).filter((groupe) => groupe.blasons.length > 0)
}

export type Selection = { mode: 'creation' } | { mode: 'edition'; id: number }

export type Panneau = { mode: 'creation' } | { mode: 'edition'; blason: Blason }

// Le panneau relit la sélection contre la liste **courante** : un blason supprimé entre-temps
// (ici ou sur un autre poste) ferme le panneau, au lieu de laisser un formulaire sur un id mort.
export function selectionCourante(
  selection: Selection | null,
  blasons: readonly Blason[],
): Panneau | null {
  if (selection === null) return null
  if (selection.mode === 'creation') return selection
  const blason = blasons.find((b) => b.id === selection.id)
  return blason === undefined ? null : { mode: 'edition', blason }
}
