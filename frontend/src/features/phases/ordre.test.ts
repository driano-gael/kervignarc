import { describe, expect, it } from 'vitest'
import { deplacer, ordreApresDeplacement, type Deplacable } from './ordre'

// Le déplacement ne lit que l'identité : le décor n'a donc rien d'autre à porter (cf. `Deplacable`).
// `ordre` reste, parce que les cas de test se lisent mieux en nommant le rang qu'on croit occuper.
function phase(id: number, ordre: number): Deplacable & { ordre: number } {
  return { id, ordre }
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
