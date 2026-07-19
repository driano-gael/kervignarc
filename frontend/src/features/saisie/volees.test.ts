import { describe, expect, it } from 'vitest'
import type { Grain, Volee } from './api'
import { libelleGrain, pointsZone, prochaineASaisir, totalVolee, voleeExistante } from './volees'

function volee(numero: number, valeurs: string[], verrouillee = false): Volee {
  return {
    numero,
    valeurs,
    saisie_par: null,
    validee_par: verrouillee ? 'ROUX' : null,
    verrouillee,
    saisie_le: null,
  }
}

describe('pointsZone', () => {
  it('« M » (manqué) vaut 0 point', () => {
    expect(pointsZone('M')).toBe(0)
  })

  it('une zone numérique vaut sa valeur', () => {
    expect(pointsZone('10')).toBe(10)
    expect(pointsZone('7')).toBe(7)
  })

  it('une valeur inattendue vaut 0 (défensif)', () => {
    expect(pointsZone('X')).toBe(0)
  })
})

describe('totalVolee', () => {
  it('somme les points des flèches', () => {
    expect(totalVolee(['10', '9', 'M'])).toBe(19)
  })

  it('une volée vide vaut 0', () => {
    expect(totalVolee([])).toBe(0)
  })
})

describe('prochaineASaisir', () => {
  it('sans aucune volée, la première est à saisir', () => {
    expect(prochaineASaisir([], 20)).toBe(1)
  })

  it('avance dès qu’une volée est saisie, même non validée (le verrou est l’acte du scoreur)', () => {
    // 1 saisie mais pas verrouillée : le marqueur passe quand même à la 2.
    expect(prochaineASaisir([volee(1, ['9', '9', '9'])], 20)).toBe(2)
  })

  it('reprend le premier trou (une volée sautée reste à saisir)', () => {
    const volees = [volee(1, ['10', '9', '8']), volee(3, ['8', '8', '8'])]
    expect(prochaineASaisir(volees, 20)).toBe(2)
  })

  it('toutes les volées saisies → on reste sur la dernière (édition via le navigateur)', () => {
    const volees = [volee(1, ['10', '9', '8']), volee(2, ['9', '9', '9'])]
    expect(prochaineASaisir(volees, 2)).toBe(2)
  })
})

describe('voleeExistante', () => {
  it('retrouve une volée déjà saisie pour la rééditer', () => {
    const v = volee(3, ['8', '8', '8'])
    expect(voleeExistante([v], 3)).toEqual(v)
  })

  it('rend null si la volée n’a pas encore été saisie', () => {
    expect(voleeExistante([], 3)).toBeNull()
  })
})

describe('libelleGrain', () => {
  it('fin de série', () => {
    expect(libelleGrain({ grain: 'fin_de_serie', n_volees: null })).toBe(
      'Validation à la fin de la série',
    )
  })

  it('toutes les N volées reprend le N', () => {
    const grain: Grain = { grain: 'toutes_les_n_volees', n_volees: 2 }
    expect(libelleGrain(grain)).toBe('Validation toutes les 2 volées')
  })

  it('grain absent → mention explicite', () => {
    expect(libelleGrain(null)).toBe('Grain de validation non défini')
  })
})
