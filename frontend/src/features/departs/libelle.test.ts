import { describe, expect, it } from 'vitest'
import { creneauRetenu, libelleCreneau } from './libelle'

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

describe('creneauRetenu', () => {
  const matin = { id: 41, numero: 1, horaire: '09:00' }
  const apresMidi = { id: 42, numero: 2, horaire: '14:00' }
  const premier = (departs: readonly { id: number }[]) => departs[0]

  it('garde le choix de l’utilisateur quand le créneau existe encore', () => {
    expect(creneauRetenu([matin, apresMidi], 42, premier)).toBe(42)
  })

  it('retombe sur le défaut quand aucun choix n’a été fait', () => {
    expect(creneauRetenu([matin, apresMidi], null, premier)).toBe(41)
  })

  it('écarte un choix dont le créneau a disparu', () => {
    // **Le défaut corrigé** : l'écran gardait `42` en mémoire après la suppression du créneau (ou
    // un changement de tournoi) et continuait d'interroger le serveur sur un identifiant mort —
    // 404 permanent, ou liste vide qui se lit comme « rien à afficher ».
    expect(creneauRetenu([matin], 42, premier)).toBe(41)
  })

  it('rend null quand il n’y a plus aucun créneau', () => {
    expect(creneauRetenu([], 42, premier)).toBeNull()
  })
})
