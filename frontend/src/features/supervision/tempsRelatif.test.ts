// Tests de `tempsRelatif` (E12US001) — « il y a N mn ». Le « maintenant » est injecté (déterminisme).

import { describe, expect, it } from 'vitest'
import { tempsRelatif } from './tempsRelatif'

const MAINTENANT = new Date('2026-03-14T09:00:00Z')

function ilYA(secondes: number): string {
  return tempsRelatif(new Date(MAINTENANT.getTime() - secondes * 1000).toISOString(), MAINTENANT)
}

describe('tempsRelatif', () => {
  it('moins d’une minute → « à l’instant »', () => {
    expect(ilYA(0)).toBe("à l'instant")
    expect(ilYA(59)).toBe("à l'instant")
  })

  it('minutes', () => {
    expect(ilYA(60)).toBe('il y a 1 mn')
    expect(ilYA(14 * 60)).toBe('il y a 14 mn')
  })

  it('heures au-delà de 60 mn', () => {
    expect(ilYA(2 * 3600)).toBe('il y a 2 h')
  })

  it('jours au-delà de 24 h', () => {
    expect(ilYA(3 * 86400)).toBe('il y a 3 j')
  })

  it('léger décalage d’horloge (instant dans le futur) → « à l’instant », pas de négatif', () => {
    expect(tempsRelatif(new Date(MAINTENANT.getTime() + 5000).toISOString(), MAINTENANT)).toBe(
      "à l'instant",
    )
  })
})
