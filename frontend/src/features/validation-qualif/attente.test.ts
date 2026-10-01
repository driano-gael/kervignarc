// Le libellé d'attente de la file du scoreur (E04US019, CA « ancienneté »).

import { describe, expect, it } from 'vitest'
import { libelleAttente } from './etat'

describe("libelleAttente — l'attente au format de la planche S07", () => {
  it('compte en secondes sous la minute', () => {
    expect(libelleAttente(35)).toBe('35 s')
    expect(libelleAttente(0)).toBe('0 s')
  })

  it('passe en minutes et secondes, secondes sur deux chiffres', () => {
    expect(libelleAttente(260)).toBe('4 min 20')
    expect(libelleAttente(65)).toBe('1 min 05')
  })

  it('passe en heures au-delà de soixante minutes', () => {
    expect(libelleAttente(3900)).toBe('1 h 05')
  })

  it('ne rend jamais une attente négative ni fractionnaire', () => {
    expect(libelleAttente(-4)).toBe('0 s')
    expect(libelleAttente(59.9)).toBe('59 s')
  })
})
