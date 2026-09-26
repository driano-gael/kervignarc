// Câblage de la destination « Inscriptions » (A09, E17US007) — revue, axe B : la définition des
// compteurs « Non placés » / « Non réglés » vit ici et dans ses hooks, et rien ne la testait.
// Intervertir les deux props laissait la porte verte. On capte les props passées à `Archers`.

import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { InscriptionsAdmin } from './InscriptionsAdmin'

const recues: { nonPlaces?: ReadonlySet<number> | null; nonRegles?: ReadonlySet<number> | null } =
  {}

vi.mock('../archers/Archers', () => ({
  Archers: (props: {
    nonPlaces: ReadonlySet<number> | null
    nonRegles: ReadonlySet<number> | null
  }) => {
    recues.nonPlaces = props.nonPlaces
    recues.nonRegles = props.nonRegles
    return null
  },
}))
vi.mock('../archers/NouvelArcher', () => ({ NouvelArcher: () => null }))
vi.mock('../archers/hooks', () => ({
  useArchers: () => ({ data: [{ id: 5 }, { id: 6 }, { id: 7 }] }),
}))
vi.mock('../paiements/hooks', () => ({ useArchersNonRegles: () => new Set([6]) }))
vi.mock('../placement/hooks', () => ({
  usePlansDuTournoi: () => [
    {
      depart_id: 1,
      cibles: [
        {
          index: 1,
          capacite: 4,
          mixite_non_garantie: false,
          cloisonnement_non_respecte: false,
          placements: [{ position: 'A', archer_id: 6, blason_id: 1, inscription_id: 60 }],
        },
      ],
      conflits: [{ archer_id: 5, raison: 'non_place', inscription_id: 50 }],
    },
  ],
}))

describe('InscriptionsAdmin — les populations des compteurs', () => {
  it('non placés : la réserve ET l’archer posé nulle part ; non réglés : le reste dû', () => {
    render(<InscriptionsAdmin tournoiId={1} ouvrir={null} onOuvrir={vi.fn()} />)

    // 5 en réserve, 7 inscrit à aucun départ, 6 posé.
    expect(recues.nonPlaces).toEqual(new Set([5, 7]))
    expect(recues.nonRegles).toEqual(new Set([6]))
  })
})
