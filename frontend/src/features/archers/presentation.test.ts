import { describe, expect, it } from 'vitest'
import type { Archer, Doublon } from './api'
import { grouperDoublons, libelleNiveau } from './presentation'

function archer(id: number): Archer {
  return {
    id,
    tournoi_id: 1,
    nom: 'Dupont',
    prenom: 'Jean',
    categorie_id: 1,
    cible: null,
    club_id: null,
  }
}

function doublon(niveau: string, a: number, b: number): Doublon {
  return { niveau, a: archer(a), b: archer(b) }
}

describe('libelleNiveau', () => {
  it('traduit les niveaux connus', () => {
    expect(libelleNiveau('probable')).toBe('Doublons probables')
    expect(libelleNiveau('a_verifier')).toBe('À vérifier')
  })

  it('retombe sur le code brut pour un niveau inconnu', () => {
    expect(libelleNiveau('autre')).toBe('autre')
  })
})

describe('grouperDoublons', () => {
  it('range les probables avant les à vérifier, quel que soit l’ordre d’entrée', () => {
    const groupes = grouperDoublons([doublon('a_verifier', 1, 3), doublon('probable', 1, 2)])
    expect(groupes.map((g) => g.niveau)).toEqual(['probable', 'a_verifier'])
    expect(groupes[0]?.paires).toHaveLength(1)
    expect(groupes[1]?.paires).toHaveLength(1)
  })

  it('n’émet pas de groupe vide', () => {
    const groupes = grouperDoublons([doublon('probable', 1, 2)])
    expect(groupes.map((g) => g.niveau)).toEqual(['probable'])
  })

  it('ne renvoie rien quand il n’y a aucun doublon', () => {
    expect(grouperDoublons([])).toEqual([])
  })
})
