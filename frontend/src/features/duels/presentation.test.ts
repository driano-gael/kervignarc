// Tests de la présentation de l'adjacence des duellistes (E03US009, ADR-0048) — logique pure, en
// node (comme `placement/presentation.test.ts`). On couvre le décompte des cibles signalées et le
// résumé chiffré affiché en bannière (accord singulier/pluriel, `null` quand rien n'est séparé).

import { describe, expect, it } from 'vitest'
import type { CiblePlaceeDuel, DuelSepare, PlanDeDuels } from './api'
import { compterAdjacenceNonGarantie, resumeAdjacenceNonGarantie } from './presentation'

function cible(over: Partial<CiblePlaceeDuel> = {}): CiblePlaceeDuel {
  return { index: 1, capacite: 4, placements: [], adjacence_non_garantie: false, ...over }
}

function plan(over: Partial<PlanDeDuels> = {}): PlanDeDuels {
  return { phase_id: 1, cibles: [], conflits: [], duels_separes: [], ...over }
}

function duel(archer_a: number, archer_b: number): DuelSepare {
  return { archer_a, archer_b }
}

describe('compterAdjacenceNonGarantie', () => {
  it('compte les cibles signalées, ignore les autres', () => {
    const cibles = [
      cible(),
      cible({ index: 2, adjacence_non_garantie: true }),
      cible({ index: 3, adjacence_non_garantie: true }),
    ]
    expect(compterAdjacenceNonGarantie(cibles)).toBe(2)
  })

  it('vaut 0 quand aucune cible n’est signalée', () => {
    expect(compterAdjacenceNonGarantie([cible(), cible({ index: 2 })])).toBe(0)
  })
})

describe('resumeAdjacenceNonGarantie', () => {
  it('renvoie null quand aucun duel n’est séparé (pas de bannière)', () => {
    expect(resumeAdjacenceNonGarantie(plan())).toBeNull()
  })

  it('accorde au singulier pour un seul duel séparé', () => {
    const resume = resumeAdjacenceNonGarantie(plan({ duels_separes: [duel(1, 2)] }))
    expect(resume).toContain('1 duel n’est pas placé côte à côte')
    expect(resume).not.toContain('duels')
  })

  it('accorde au pluriel pour plusieurs duels séparés', () => {
    const resume = resumeAdjacenceNonGarantie(plan({ duels_separes: [duel(1, 2), duel(3, 4)] }))
    expect(resume).toContain('2 duels ne sont pas placés côte à côte')
  })
})
