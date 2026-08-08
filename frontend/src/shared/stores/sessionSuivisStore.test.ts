// Tests du `sessionSuivisStore` (E07US006) — la liste d'archers suivis mémorisée localement.
//
// Contrat dérivé du CA « suivre » : suivre ajoute, ne plus suivre retire l'archer visé et lui seul,
// re-suivre est idempotent (pas de doublon), et la liste peut porter des archers de tournois
// différents (tournois concurrents). Tests en node : le store est importable sans DOM.

import { beforeEach, describe, expect, it } from 'vitest'
import { useSessionSuivisStore } from './sessionSuivisStore'

beforeEach(() => {
  // ⚠️ **Repartir de l'état initial du store**, plutôt que de réécrire ses valeurs à la main
  // (correctif de revue) : un état ajouté au store et oublié ici fuite d'un test au suivant, et
  // l'ordre d'exécution décide alors du résultat. `getInitialState()` ne peut pas se désynchroniser
  // du store — et il évite qu'un `beforeEach` finisse par **poser** la valeur qu'un test vérifie.
  useSessionSuivisStore.setState(useSessionSuivisStore.getInitialState())
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

  it('migre un appareil qui a déjà stocké la préférence désarmée, sans perdre ses suivis', async () => {
    // ⚠️ Le point le plus risqué de la 2ᵉ passe, et le seul qui était resté sans test (relevé en
    // 3ᵉ passe). `persist` fusionne superficiellement : une clé **absente** retombe sur la valeur
    // initiale — mais un premier jet de cette US avait déjà **écrit** `centrerSurSuivis: false`
    // dans le `localStorage` de tout appareil ayant ouvert la branche, à commencer par celui du
    // commanditaire et celui de la recette. Là, la valeur stockée gagne : sans `migrate`,
    // l'arbitrage aurait été invisible précisément sur les machines qui comptent, et se serait
    // diagnostiqué en « le correctif ne marche pas ».
    localStorage.setItem(
      'kervignarc-session-suivis',
      JSON.stringify({
        state: { suivis: [{ archerId: 1, tournoiId: 1 }], centrerSurSuivis: false },
        version: 0,
      }),
    )

    await useSessionSuivisStore.persist.rehydrate()

    expect(useSessionSuivisStore.getState().centrerSurSuivis).toBe(true)
    // La migration ne touche **que** la préférence : personne ne perd les archers qu'il suit.
    expect(useSessionSuivisStore.getState().suivis).toEqual([{ archerId: 1, tournoiId: 1 }])
    // Et le store reste utilisable : un état migré amputé de ses actions ferait un écran mort.
    expect(typeof useSessionSuivisStore.getState().nePlusSuivre).toBe('function')

    localStorage.clear()
  })

  it('respecte un choix déjà migré : « tout le tournoi » ne se réarme pas tout seul', async () => {
    // Symétrique indispensable : sans lui, une migration qui écrase la préférence **à chaque**
    // rechargement passerait aussi. Le spectateur qui a choisi « Tout le tournoi » doit le
    // retrouver, c'est tout l'objet d'une préférence persistée.
    localStorage.setItem(
      'kervignarc-session-suivis',
      JSON.stringify({ state: { suivis: [], centrerSurSuivis: false }, version: 1 }),
    )

    await useSessionSuivisStore.persist.rehydrate()

    expect(useSessionSuivisStore.getState().centrerSurSuivis).toBe(false)

    localStorage.clear()
  })

  it('centrer bascule la préférence sans toucher la liste', () => {
    useSessionSuivisStore.getState().suivre({ archerId: 7, tournoiId: 1 })

    useSessionSuivisStore.getState().centrer(false)

    expect(useSessionSuivisStore.getState().centrerSurSuivis).toBe(false)
    expect(useSessionSuivisStore.getState().suivis).toEqual([{ archerId: 7, tournoiId: 1 }])
  })
})
