// Non-régression E00US024 : l'oracle est le comportement de l'atelier avant l'extraction.

import { describe, expect, it } from 'vitest'

import type { FormatTournoi } from '../patrimoine/api'
import { armesDeLaBibliotheque, formatChoisi } from './bibliotheque'

function format(id: number): FormatTournoi {
  return { id, nom: `F${id}`, origine: 'utilisateur', etapes: [], effectif_minimum_exige: null }
}

describe('formatChoisi', () => {
  it('rend le format explicitement choisi', () => {
    expect(formatChoisi([format(1), format(2)], 2)?.id).toBe(2)
  })

  it('retombe sur le premier sans choix, ou si le choix a disparu', () => {
    expect(formatChoisi([format(1), format(2)], null)?.id).toBe(1)
    expect(formatChoisi([format(1), format(2)], 99)?.id).toBe(1)
  })

  it('rend null sans bibliothèque chargée ou vide', () => {
    expect(formatChoisi(undefined, 1)).toBeNull()
    expect(formatChoisi([], null)).toBeNull()
  })
})

describe('armesDeLaBibliotheque', () => {
  it('signale l’erreur en priorité, même avec des données', () => {
    expect(armesDeLaBibliotheque(true, [{ arme: 'Arc nu' }])).toBe('erreur')
  })

  it('signale le chargement tant que les catégories manquent', () => {
    expect(armesDeLaBibliotheque(false, undefined)).toBe('chargement')
  })

  it('rend les armes distinctes des catégories, sans les nulles', () => {
    expect(
      armesDeLaBibliotheque(false, [{ arme: 'Arc nu' }, { arme: null }, { arme: 'Arc nu' }]),
    ).toEqual(['Arc nu'])
    expect(armesDeLaBibliotheque(false, [])).toEqual([])
  })
})
