// Tests du `sessionSuivisStore` (E07US006) — la liste d'archers suivis mémorisée localement.
//
// Contrat dérivé du CA « suivre » : suivre ajoute, ne plus suivre retire l'archer visé et lui seul,
// re-suivre est idempotent (pas de doublon), et la liste peut porter des archers de tournois
// différents (tournois concurrents). Tests en node : le store est importable sans DOM.

import { beforeEach, describe, expect, it } from 'vitest'
import { useSessionSuivisStore } from './sessionSuivisStore'

beforeEach(() => {
  // ⚠️ **Remettre aussi `centrerSurSuivis`** (correctif de revue) : un état ajouté au store et
  // oublié ici fuite d'un test au suivant, et l'ordre d'exécution décide alors du résultat. Le
  // défaut ne se voit pas tant qu'aucun test ne l'arme — c'est-à-dire jusqu'au prochain.
  useSessionSuivisStore.setState({ suivis: [], centrerSurSuivis: true })
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

  it('la préférence d’affichage est armée d’entrée (CA E07US005, D-09)', () => {
    // Le CA d'E07US005 veut « Mon chemin » **par défaut dès qu'on suit quelqu'un » ; E16US004 ayant
    // remonté ce choix dans un interrupteur unique, c'est cette valeur initiale qui le porte
    // désormais — pour les cinq vues publiques à la fois (arbitrage du 08/08/2026).
    expect(useSessionSuivisStore.getInitialState().centrerSurSuivis).toBe(true)
  })

  it('centrer bascule la préférence sans toucher la liste', () => {
    useSessionSuivisStore.getState().suivre({ archerId: 7, tournoiId: 1 })

    useSessionSuivisStore.getState().centrer(false)

    expect(useSessionSuivisStore.getState().centrerSurSuivis).toBe(false)
    expect(useSessionSuivisStore.getState().suivis).toEqual([{ archerId: 7, tournoiId: 1 }])
  })
})
