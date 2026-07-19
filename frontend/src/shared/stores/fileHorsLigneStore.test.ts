// Tests du `fileHorsLigneStore` (E04US009, ADR-0037) — mise en file, remplacement par volée,
// confirmation (retrait), drapeau de synchronisation. Environnement node : on pilote le store via
// `getState()/setState()` (comme `sessionPosteStore.test`), sans DOM.

import { beforeEach, describe, expect, it } from 'vitest'
import { remplacerOuAjouter, useFileHorsLigneStore, type VoleeEnFile } from './fileHorsLigneStore'

function corps(numero: number, identifiant: string, archer = 7): VoleeEnFile {
  return {
    tournoi_id: 1,
    archer_id: archer,
    numero,
    valeurs: ['10', '9', '9'],
    saisie_par: 'DURAND',
    identifiant_saisie: identifiant,
  }
}

beforeEach(() => {
  useFileHorsLigneStore.setState({ enAttente: [], synchronisation: false })
})

describe('remplacerOuAjouter (pur)', () => {
  it('ajoute une nouvelle volée en fin de file (FIFO)', () => {
    const file = remplacerOuAjouter([corps(1, 'a')], corps(2, 'b'))
    expect(file.map((c) => c.numero)).toEqual([1, 2])
  })

  it('remplace l’attente pour la MÊME volée (même cible/archer/numéro), sans doublon', () => {
    const file = remplacerOuAjouter([corps(1, 'a')], corps(1, 'b'))
    expect(file.map((c) => c.identifiant_saisie)).toEqual(['b'])
  })

  it('ne confond pas deux archers différents sur le même numéro', () => {
    const file = remplacerOuAjouter([corps(1, 'a', 7)], corps(1, 'b', 8))
    expect(file).toHaveLength(2)
  })
})

describe('fileHorsLigneStore', () => {
  it('mettreEnFile empile les saisies', () => {
    useFileHorsLigneStore.getState().mettreEnFile(corps(1, 'a'))
    useFileHorsLigneStore.getState().mettreEnFile(corps(2, 'b'))
    expect(useFileHorsLigneStore.getState().enAttente).toHaveLength(2)
  })

  it('confirmer retire la saisie par son identifiant (rejeu réussi ou refus définitif)', () => {
    useFileHorsLigneStore.getState().mettreEnFile(corps(1, 'a'))
    useFileHorsLigneStore.getState().mettreEnFile(corps(2, 'b'))

    useFileHorsLigneStore.getState().confirmer('a')

    const reste = useFileHorsLigneStore.getState().enAttente
    expect(reste.map((c) => c.identifiant_saisie)).toEqual(['b'])
  })

  it('demarrerSync / terminerSync bascule le drapeau de synchronisation', () => {
    useFileHorsLigneStore.getState().demarrerSync()
    expect(useFileHorsLigneStore.getState().synchronisation).toBe(true)
    useFileHorsLigneStore.getState().terminerSync()
    expect(useFileHorsLigneStore.getState().synchronisation).toBe(false)
  })
})
