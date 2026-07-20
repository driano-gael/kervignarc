// Tests de `etatIndicateur` (E00US010 + E04US009) — dérivation pure de l'état affiché à partir du
// lien WebSocket et de la file hors-ligne. Les trois états du CA (connecté / hors-ligne /
// synchronisation) plus le détail « N en attente ».

import { describe, expect, it } from 'vitest'
import { etatIndicateur } from './indicateur'

describe('etatIndicateur', () => {
  it('lien connecté, rien en attente → « En ligne »', () => {
    expect(etatIndicateur('connecte', 0, false)).toEqual({
      classe: 'connecte',
      libelle: 'En ligne',
    })
  })

  it('lien en cours de connexion → « Connexion… »', () => {
    expect(etatIndicateur('connexion', 0, false)).toEqual({
      classe: 'connexion',
      libelle: 'Connexion…',
    })
  })

  it('lien perdu, rien en attente → « Hors ligne »', () => {
    expect(etatIndicateur('deconnecte', 0, false)).toEqual({
      classe: 'deconnecte',
      libelle: 'Hors ligne',
    })
  })

  it('des saisies en attente signalent le retard, même si le lien paraît revenu', () => {
    expect(etatIndicateur('connecte', 2, false)).toEqual({
      classe: 'deconnecte',
      libelle: 'Hors ligne · 2 saisies en attente',
    })
  })

  it('une seule saisie en attente : libellé au singulier', () => {
    expect(etatIndicateur('deconnecte', 1, false)).toEqual({
      classe: 'deconnecte',
      libelle: 'Hors ligne · 1 saisie en attente',
    })
  })

  it('un rejeu en cours prime sur tout → « Synchronisation… »', () => {
    expect(etatIndicateur('connecte', 3, true)).toEqual({
      classe: 'synchronisation',
      libelle: 'Synchronisation… (3 saisies en attente)',
    })
  })
})
