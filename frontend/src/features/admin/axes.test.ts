// Tests de la lecture d'axe et de destination depuis l'adresse (E14US003, ADR-0058). Partie pure.

import { describe, expect, it } from 'vitest'
import { AXES, axeDepuisSegments, destinationDepuisSegments, destinationParDefaut } from './axes'
import type { DestinationAdminId } from './aide-ecrans'

describe('axeDepuisSegments', () => {
  it('sans segment : accueil de l’admin (aucun axe ouvert)', () => {
    expect(axeDepuisSegments([])).toBeNull()
  })

  it.each(['atelier', 'pilotage', 'gestion'] as const)('reconnaît l’axe %s', (axe) => {
    expect(axeDepuisSegments([axe])).toBe(axe)
    expect(axeDepuisSegments([axe, 'peu-importe'])).toBe(axe)
  })

  it('un axe inconnu retombe sur l’accueil, pas sur une page vide', () => {
    expect(axeDepuisSegments(['preparation'])).toBeNull()
    expect(axeDepuisSegments(['jourj'])).toBeNull()
  })
})

describe('destinationDepuisSegments', () => {
  const DU_PILOTAGE: DestinationAdminId[] = ['accueil', 'supervision', 'completude']

  it('reconnaît une destination proposée par l’axe', () => {
    expect(destinationDepuisSegments(['pilotage', 'supervision'], DU_PILOTAGE)).toBe('supervision')
  })

  it('sans second segment : rien, l’axe choisira son ouverture', () => {
    expect(destinationDepuisSegments(['pilotage'], DU_PILOTAGE)).toBeNull()
  })

  it('REFUSE une destination qui appartient à un autre axe', () => {
    // Sans ce garde, /admin/atelier/supervision afficherait un écran de pilotage sous l'intitulé
    // « Atelier » — exactement le mélange que le découpage en axes supprime.
    expect(
      destinationDepuisSegments(['atelier', 'supervision'], ['categories', 'blasons']),
    ).toBeNull()
  })
})

describe('destinationParDefaut', () => {
  it('le pilotage ouvre sur le tableau de bord (D-20)', () => {
    expect(destinationParDefaut('pilotage')).toBe('accueil')
  })

  it('chaque axe a une ouverture définie', () => {
    for (const { axe } of AXES) {
      expect(destinationParDefaut(axe)).toBeTruthy()
    }
  })
})
