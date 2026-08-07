import { describe, expect, it } from 'vitest'
import { libelleCreneau } from './libelle'

describe('libelleCreneau', () => {
  it('nomme un créneau par son numéro et son horaire', () => {
    expect(libelleCreneau({ id: 3, numero: 2, horaire: '14:00' })).toBe('Départ 2 — 14:00')
  })

  it('se passe de l’horaire quand il manque', () => {
    // L'horaire est obligatoire en base depuis la migration 0032, mais le DTO le laisse nullable :
    // concaténer sans garde afficherait « Départ 2 — null » sur les données d'avant.
    expect(libelleCreneau({ id: 3, numero: 2, horaire: null })).toBe('Départ 2')
  })
})
