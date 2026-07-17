import { describe, expect, it } from 'vitest'
import type { Zone } from './api'
import { aUneZoneMarquante, basculerZone } from './zones'

describe('basculerZone', () => {
  it('replace une zone cochée dans l’ordre canonique, quel que soit l’ordre d’arrivée', () => {
    // L'admin coche 6 en dernier : il doit ressortir à sa place, pas à la fin.
    const actuelles: Zone[] = ['M', '9', '10']
    expect(basculerZone(actuelles, '6')).toEqual(['10', '9', '6', 'M'])
  })

  it('décoche sans dénormaliser l’ordre', () => {
    const actuelles: Zone[] = ['10', '9', '8', '7', '6', 'M']
    expect(basculerZone(actuelles, '8')).toEqual(['10', '9', '7', '6', 'M'])
  })

  it('ne duplique pas une zone déjà cochée (bascule aller-retour)', () => {
    const actuelles: Zone[] = ['10', '9', 'M']
    expect(basculerZone(basculerZone(actuelles, '8'), '8')).toEqual(actuelles)
  })

  it('ne mute pas le tableau reçu', () => {
    const actuelles: Zone[] = ['10', 'M']
    basculerZone(actuelles, '9')
    expect(actuelles).toEqual(['10', 'M'])
  })

  it('reconstitue le triple 40 en retirant 5 → 1 du jeu complet', () => {
    let zones: Zone[] = [...ZONES_COMPLETES]
    for (const zone of ['5', '4', '3', '2', '1'] as Zone[]) {
      zones = basculerZone(zones, zone)
    }
    expect(zones).toEqual(['10', '9', '8', '7', '6', 'M'])
  })
})

describe('aUneZoneMarquante', () => {
  it('est faux quand il ne reste que le manqué', () => {
    expect(aUneZoneMarquante(['M'])).toBe(false)
  })

  it('est faux sur un jeu vide', () => {
    expect(aUneZoneMarquante([])).toBe(false)
  })

  it('est vrai dès qu’une valeur chiffrée subsiste', () => {
    expect(aUneZoneMarquante(['6', 'M'])).toBe(true)
  })
})

const ZONES_COMPLETES: Zone[] = ['10', '9', '8', '7', '6', '5', '4', '3', '2', '1', 'M']
