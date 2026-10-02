import { describe, expect, it } from 'vitest'

import { decrireDuree, decrireHeure, depuisDureePrevue, versDureePrevue } from './horaires'

describe('horaires', () => {
  it('un champ vide vaut une durée inconnue, et réciproquement', () => {
    expect(versDureePrevue('  ')).toBeNull()
    expect(versDureePrevue('90')).toBe(90)
    expect(depuisDureePrevue(null)).toBe('')
    expect(depuisDureePrevue(90)).toBe('90')
  })

  it('dit une durée comme un organisateur la dit', () => {
    expect(decrireDuree(45)).toBe('45 min')
    expect(decrireDuree(120)).toBe('2 h')
    expect(decrireDuree(95)).toBe('1 h 35')
    expect(decrireDuree(65)).toBe('1 h 05')
  })

  it('signale le lendemain et tait l’inconnu', () => {
    expect(decrireHeure(null)).toBe('—')
    expect(decrireHeure({ heure: '09:30', jours_apres: 0 })).toBe('09:30')
    expect(decrireHeure({ heure: '00:30', jours_apres: 1 })).toBe('00:30 (lendemain)')
    expect(decrireHeure({ heure: '01:00', jours_apres: 2 })).toBe('01:00 (J+2)')
  })
})
