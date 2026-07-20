// Tests du `sessionSuivisStore` (E07US006) — la liste d'archers suivis mémorisée localement.
//
// Contrat dérivé du CA « suivre » : suivre ajoute, ne plus suivre retire l'archer visé et lui seul,
// re-suivre est idempotent (pas de doublon), et la liste peut porter des archers de tournois
// différents (tournois concurrents). Tests en node : le store est importable sans DOM.

import { beforeEach, describe, expect, it } from 'vitest'
import { useSessionSuivisStore } from './sessionSuivisStore'

beforeEach(() => {
  useSessionSuivisStore.setState({ suivis: [] })
})

describe('sessionSuivisStore — liste d’archers suivis', () => {
  it('suivre ajoute un archer à la liste', () => {
    useSessionSuivisStore.getState().suivre({ archerId: 7, tournoiId: 1 })

    expect(useSessionSuivisStore.getState().suivis).toEqual([{ archerId: 7, tournoiId: 1 }])
  })

  it('suivre est idempotent : re-suivre le même archer ne le duplique pas', () => {
    useSessionSuivisStore.getState().suivre({ archerId: 7, tournoiId: 1 })
    useSessionSuivisStore.getState().suivre({ archerId: 7, tournoiId: 1 })

    expect(useSessionSuivisStore.getState().suivis).toEqual([{ archerId: 7, tournoiId: 1 }])
  })

  it('nePlusSuivre retire l’archer visé et lui seul', () => {
    useSessionSuivisStore.getState().suivre({ archerId: 7, tournoiId: 1 })
    useSessionSuivisStore.getState().suivre({ archerId: 9, tournoiId: 1 })

    useSessionSuivisStore.getState().nePlusSuivre(7)

    expect(useSessionSuivisStore.getState().suivis).toEqual([{ archerId: 9, tournoiId: 1 }])
  })

  it('la liste porte des archers de tournois différents (tournois concurrents)', () => {
    useSessionSuivisStore.getState().suivre({ archerId: 7, tournoiId: 1 })
    useSessionSuivisStore.getState().suivre({ archerId: 3, tournoiId: 2 })

    expect(useSessionSuivisStore.getState().suivis).toEqual([
      { archerId: 7, tournoiId: 1 },
      { archerId: 3, tournoiId: 2 },
    ])
  })
})
