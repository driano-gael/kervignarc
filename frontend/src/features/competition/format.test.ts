// Tests du convertisseur d'argent (E00US014, résorbe DETTE-005). Oracle : les CA d'E00US014
// (stories/E00-socle.md) et la règle **centimes entiers** d'ADR-0012 — pas l'implémentation.
// Le risque que ces tests existent pour couvrir : une inversion `padEnd`/`padStart` fausserait
// silencieusement le montant dû (8,10 € → 8,01 €) en passant `tsc`, ESLint et la revue (EF-8.1).
import { describe, expect, it } from 'vitest'

import { centimesVersSaisieEuros, decrireTarif, saisieEurosVersCentimes } from './format'

describe('saisieEurosVersCentimes', () => {
  it('convertit un entier d’euros en centimes', () => {
    expect(saisieEurosVersCentimes('0')).toBe(0)
    expect(saisieEurosVersCentimes('8')).toBe(800)
  })

  it('complète les décimales à droite (810, pas 801)', () => {
    // Le cœur de la dette : « 8,1 » vaut 8,10 € = 810 centimes. Un `padStart` donnerait 801.
    expect(saisieEurosVersCentimes('8,1')).toBe(810)
    expect(saisieEurosVersCentimes('8,10')).toBe(810)
  })

  it('gère les petits montants sans perdre le zéro de tête', () => {
    expect(saisieEurosVersCentimes('0,05')).toBe(5)
  })

  it('accepte le point comme la virgule', () => {
    expect(saisieEurosVersCentimes('8.1')).toBe(810)
    expect(saisieEurosVersCentimes('8.10')).toBe(810)
    expect(saisieEurosVersCentimes('8.1')).toBe(saisieEurosVersCentimes('8,1'))
  })

  it('refuse (→ null) toute saisie qui n’est pas un montant à ≤ 2 décimales', () => {
    expect(saisieEurosVersCentimes('8,105')).toBeNull() // 3 décimales
    expect(saisieEurosVersCentimes('-8')).toBeNull() // négatif
    expect(saisieEurosVersCentimes('huit')).toBeNull() // non numérique
    expect(saisieEurosVersCentimes('8,')).toBeNull() // séparateur sans décimale
    expect(saisieEurosVersCentimes('')).toBeNull() // vide
  })
})

describe('centimesVersSaisieEuros', () => {
  it('réémet une saisie éditable, décimales sur deux chiffres', () => {
    expect(centimesVersSaisieEuros(0)).toBe('0,00')
    expect(centimesVersSaisieEuros(5)).toBe('0,05') // padStart : le zéro de tête est à gauche
    expect(centimesVersSaisieEuros(50)).toBe('0,50')
    expect(centimesVersSaisieEuros(800)).toBe('8,00')
    expect(centimesVersSaisieEuros(810)).toBe('8,10')
  })
})

describe('aller-retour centimes → saisie → centimes', () => {
  // Un tarif relu dans le formulaire puis renvoyé ne doit pas changer de valeur : sinon éditer un
  // départ le modifierait à son insu. Le cas **0** est explicite au CA (éditer un créneau gratuit
  // ne doit pas l’effacer).
  it.each([0, 5, 50, 800, 810, 12345])('est stable pour %i centimes', (centimes) => {
    expect(saisieEurosVersCentimes(centimesVersSaisieEuros(centimes))).toBe(centimes)
  })
})

describe('decrireTarif', () => {
  it('distingue le gratuit d’un montant (ADR-0017)', () => {
    expect(decrireTarif(0)).toBe('Gratuit')
    expect(decrireTarif(810)).toBe('8,10 €')
    expect(decrireTarif(5)).toBe('0,05 €')
  })
})
