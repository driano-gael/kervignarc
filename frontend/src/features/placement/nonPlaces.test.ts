// « Non placés » (A09, E17US007) — revue, axes B, C1, D : la 1ʳᵉ version comptait la réserve des
// plans seulement, donc ignorait l'archer inscrit à AUCUN départ (celui qu'on a oublié) et
// affichait « ? » avant la création du gabarit, alors que personne n'est placé.

import { describe, expect, it } from 'vitest'
import type { PlanDeCibles } from './api'
import { archersNonPlaces } from './nonPlaces'

const plan = (poses: number[], reserve: number[]): PlanDeCibles => ({
  depart_id: 1,
  cibles: [
    {
      index: 1,
      capacite: 4,
      mixite_non_garantie: false,
      cloisonnement_non_respecte: false,
      placements: poses.map((archer_id, i) => ({
        position: 'ABCD'[i] ?? 'A',
        archer_id,
        blason_id: 1,
        inscription_id: archer_id * 10,
      })),
    },
  ],
  conflits: reserve.map((archer_id) => ({
    archer_id,
    raison: 'non_place',
    inscription_id: archer_id * 10,
  })),
})

describe('archersNonPlaces', () => {
  it('un archer en réserve est non placé', () => {
    expect(archersNonPlaces([1, 2], [plan([1], [2])])).toEqual(new Set([2]))
  })

  it('un archer inscrit à aucun départ est non placé — c’est l’oublié', () => {
    expect(archersNonPlaces([1, 3], [plan([1], [])])).toEqual(new Set([3]))
  })

  it('posé sur un départ mais en réserve sur un autre : il lui manque une cible', () => {
    expect(archersNonPlaces([1], [plan([1], []), plan([], [1])])).toEqual(new Set([1]))
  })

  it('sans gabarit de salle, personne n’a de cible : tous sont non placés', () => {
    expect(archersNonPlaces([1, 2], 'sans_gabarit')).toEqual(new Set([1, 2]))
  })

  it('une lecture de plan en échec : population inconnue, jamais un compte partiel', () => {
    expect(archersNonPlaces([1, 2], null)).toBeNull()
  })
})
