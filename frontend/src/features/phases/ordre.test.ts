import { describe, expect, it } from 'vitest'
import type { Phase } from './api'
import { deplacer, ordreApresDeplacement } from './ordre'

function phase(id: number, ordre: number): Phase {
  return {
    id,
    tournoi_id: 1,
    ordre,
    type: 'elimination_directe',
    statut: 'a_venir',
    sources: [],
    effectif: null,
    barrage_jusqu_au: null,
    profondeur: null,
  }
}

describe('deplacer', () => {
  it('déplace un élément vers le haut', () => {
    expect(deplacer(['a', 'b', 'c'], 2, 0)).toEqual(['c', 'a', 'b'])
  })

  it('déplace un élément vers le bas', () => {
    expect(deplacer(['a', 'b', 'c'], 0, 1)).toEqual(['b', 'a', 'c'])
  })

  it('laisse la liste inchangée hors bornes', () => {
    expect(deplacer(['a', 'b'], 0, 5)).toEqual(['a', 'b'])
    expect(deplacer(['a', 'b'], -1, 0)).toEqual(['a', 'b'])
  })
})

describe('ordreApresDeplacement', () => {
  const phases = [phase(10, 1), phase(20, 2), phase(30, 3)]

  it('monte une phase d’un cran', () => {
    expect(ordreApresDeplacement(phases, 20, 'monter')).toEqual([20, 10, 30])
  })

  it('descend une phase d’un cran', () => {
    expect(ordreApresDeplacement(phases, 20, 'descendre')).toEqual([10, 30, 20])
  })

  it('renvoie null quand la phase est déjà en tête et qu’on la monte', () => {
    expect(ordreApresDeplacement(phases, 10, 'monter')).toBeNull()
  })

  it('renvoie null quand la phase est déjà en queue et qu’on la descend', () => {
    expect(ordreApresDeplacement(phases, 30, 'descendre')).toBeNull()
  })

  it('renvoie null pour une phase inconnue', () => {
    expect(ordreApresDeplacement(phases, 999, 'monter')).toBeNull()
  })
})
