// Taille d'un blason en déroulante de fractions (E00US016, CA « fractions de blason en
// déroulante ») — tests écrits depuis le CA, avant le module.

import { describe, expect, it } from 'vitest'
import { AUTRE, FRACTIONS, choixDeTaille, libelleTaille, tailleDuChoix } from './taille'

describe('FRACTIONS — les quatre tailles proposées', () => {
  it('propose cible entière, demi, tiers et quart, dans cet ordre', () => {
    expect(FRACTIONS.map((fraction) => fraction.valeur)).toEqual([1, 1 / 2, 1 / 3, 1 / 4])
  })
})

describe('choixDeTaille — ce que la déroulante affiche pour une taille enregistrée', () => {
  it('reconnaît chaque fraction proposée', () => {
    expect(choixDeTaille(1)).toBe('1')
    expect(choixDeTaille(0.5)).toBe('2')
    expect(choixDeTaille(0.25)).toBe('4')
  })

  it('reconnaît un tiers malgré l’arrondi flottant du serveur', () => {
    expect(choixDeTaille(0.3333333333333333)).toBe('3')
    expect(choixDeTaille(0.33333333334)).toBe('3')
  })

  it('range toute autre taille sous « Autre… »', () => {
    expect(choixDeTaille(0.75)).toBe(AUTRE)
    expect(choixDeTaille(0.33)).toBe(AUTRE)
  })
})

describe('tailleDuChoix — la valeur envoyée au serveur', () => {
  it('envoie la fraction exacte d’un choix de la liste', () => {
    expect(tailleDuChoix('3', '')).toBe(1 / 3)
    expect(tailleDuChoix('1', '0,2')).toBe(1)
  })

  it('lit le réel libre sous « Autre… », virgule comprise', () => {
    expect(tailleDuChoix(AUTRE, '0,75')).toBe(0.75)
    expect(tailleDuChoix(AUTRE, '0.6')).toBe(0.6)
  })

  it('refuse un réel libre vide, non numérique ou hors de ]0, 1]', () => {
    expect(tailleDuChoix(AUTRE, '')).toBeNull()
    expect(tailleDuChoix(AUTRE, 'demi')).toBeNull()
    expect(tailleDuChoix(AUTRE, '0')).toBeNull()
    expect(tailleDuChoix(AUTRE, '1,5')).toBeNull()
  })
})

describe('libelleTaille — la colonne « Taille » de la liste', () => {
  it('affiche le symbole d’une fraction connue', () => {
    expect(libelleTaille(1)).toBe('1')
    expect(libelleTaille(0.5)).toBe('½')
    expect(libelleTaille(1 / 3)).toBe('⅓')
    expect(libelleTaille(0.25)).toBe('¼')
  })

  it('affiche une autre taille en décimal français', () => {
    expect(libelleTaille(0.75)).toBe('0,75')
  })
})
