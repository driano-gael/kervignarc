// Tests de la présentation de la mixité de club (E03US006, RG-3) — logique pure, en node (comme
// `planConsultation.test.ts`). On couvre le décompte des cibles signalées et le résumé chiffré
// affiché en bannière (accord singulier/pluriel, `null` quand tout est mixé).

import { describe, expect, it } from 'vitest'
import type { CiblePlacee } from './api'
import { compterMixiteNonGarantie, resumeMixiteNonGarantie } from './presentation'

function cible(over: Partial<CiblePlacee> = {}): CiblePlacee {
  return { index: 1, capacite: 4, placements: [], mixite_non_garantie: false, ...over }
}

describe('compterMixiteNonGarantie', () => {
  it('compte les cibles signalées, ignore les autres', () => {
    const cibles = [
      cible(),
      cible({ index: 2, mixite_non_garantie: true }),
      cible({ index: 3, mixite_non_garantie: true }),
    ]
    expect(compterMixiteNonGarantie(cibles)).toBe(2)
  })

  it('vaut 0 quand aucune cible n’est signalée', () => {
    expect(compterMixiteNonGarantie([cible(), cible({ index: 2 })])).toBe(0)
  })
})

describe('resumeMixiteNonGarantie', () => {
  it('renvoie null quand la mixité est garantie partout (pas de bannière)', () => {
    expect(resumeMixiteNonGarantie([cible(), cible({ index: 2 })])).toBeNull()
  })

  it('accorde au singulier pour une seule cible', () => {
    const resume = resumeMixiteNonGarantie([cible({ mixite_non_garantie: true })])
    expect(resume).toContain('1 cible sans')
    expect(resume).not.toContain('cibles')
  })

  it('accorde au pluriel pour plusieurs cibles', () => {
    const resume = resumeMixiteNonGarantie([
      cible({ mixite_non_garantie: true }),
      cible({ index: 2, mixite_non_garantie: true }),
    ])
    expect(resume).toContain('2 cibles sans')
  })
})
