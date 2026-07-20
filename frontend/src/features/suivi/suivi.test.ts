// Tests de la logique pure de « suivi » (E07US006), dérivés du CA : « recherche par nom » et « une
// carte par archer avec cible/position ». En node, sans composant.

import { describe, expect, it } from 'vitest'
import type { Archer } from '../competition/api'
import type { PlanDeCibles } from '../placement/api'
import { filtrerArchers, placeDansPlan } from './suivi'

const archer = (id: number, nom: string, prenom: string): Archer => ({
  id,
  tournoi_id: 1,
  nom,
  prenom,
  categorie_id: 1,
  cible: null,
  club_id: null,
})

describe('filtrerArchers — recherche par nom', () => {
  const archers = [
    archer(1, 'Martin', 'Paul'),
    archer(2, 'Durand', 'Rémy'),
    archer(3, 'Martinez', 'Sophie'),
  ]

  it('une requête vide ne propose rien (la recherche est l’exception, pas la porte)', () => {
    expect(filtrerArchers(archers, '')).toEqual([])
    expect(filtrerArchers(archers, '   ')).toEqual([])
  })

  it('matche sur le nom, insensible à la casse', () => {
    expect(filtrerArchers(archers, 'mart').map((a) => a.id)).toEqual([1, 3])
  })

  it('matche aussi sur le prénom', () => {
    expect(filtrerArchers(archers, 'sophie').map((a) => a.id)).toEqual([3])
  })

  it('tolère les accents (« remy » retrouve « Rémy »)', () => {
    expect(filtrerArchers(archers, 'remy').map((a) => a.id)).toEqual([2])
  })

  it('sans correspondance, renvoie une liste vide', () => {
    expect(filtrerArchers(archers, 'zzz')).toEqual([])
  })
})

describe('placeDansPlan — place d’un archer sur un départ', () => {
  const plan: PlanDeCibles = {
    depart_id: 10,
    cibles: [
      {
        index: 1,
        capacite: 4,
        placements: [{ position: 'A', archer_id: 1, blason_id: 1, inscription_id: 100 }],
      },
      {
        index: 2,
        capacite: 4,
        placements: [{ position: 'C', archer_id: 2, blason_id: 1, inscription_id: 101 }],
      },
    ],
    conflits: [],
  }

  it('archer posé → sa cible et sa position', () => {
    expect(placeDansPlan(plan, 2)).toEqual({ cible: 2, position: 'C' })
  })

  it('archer absent du plan (en réserve) → null', () => {
    expect(placeDansPlan(plan, 3)).toBeNull()
  })

  it('plan sans cible → null', () => {
    expect(placeDansPlan({ depart_id: 10, cibles: [], conflits: [] }, 1)).toBeNull()
  })
})
