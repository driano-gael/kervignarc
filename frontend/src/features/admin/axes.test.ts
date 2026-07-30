// Tests des axes de l'admin et de la lecture d'adresse (E14US003, ADR-0058/0059). Partie pure.

import { describe, expect, it } from 'vitest'
import {
  AXES,
  AXE_PAR_DESTINATION,
  analyserSegmentsAdmin,
  destinationParDefaut,
  destinationValide,
  segmentsAdmin,
  type Axe,
} from './axes'
import { AIDE_ECRANS, type DestinationAdminId } from './aide-ecrans'

describe('répartition des destinations', () => {
  it('CA — les 25 destinations livrées sont toutes rangées, aucune perdue', () => {
    // Le risque n°1 de cette US : 24 destinations réétiquetées à la main. Une entrée oubliée
    // disparaîtrait **silencieusement** de la sidebar (elle est filtrée par axe), sans que `tsc`
    // ni aucun autre test ne le voie.
    const rangees = Object.keys(AXE_PAR_DESTINATION)
    const toutes = Object.keys(AIDE_ECRANS)
    expect(toutes).toHaveLength(25)
    expect(rangees).toHaveLength(24)
    // La 25ᵉ est « tournoi » : elle n'appartient à aucun axe, c'est l'assemblage porté par l'accueil.
    expect(toutes.filter((d) => !rangees.includes(d))).toEqual(['tournoi'])
  })

  it('chaque destination est rangée dans un axe connu', () => {
    const axes = new Set(Object.values(AXE_PAR_DESTINATION))
    expect(axes).toEqual(new Set<Axe>(['atelier', 'pilotage', 'gestion']))
  })

  it('CA — l’atelier ne travaille pas sur un tournoi ; le pilotage et la gestion, si', () => {
    expect(AXES.find((a) => a.axe === 'atelier')!.besoinTournoi).toBe(false)
    expect(AXES.find((a) => a.axe === 'pilotage')!.besoinTournoi).toBe(true)
    expect(AXES.find((a) => a.axe === 'gestion')!.besoinTournoi).toBe(true)
  })
})

describe('destinationParDefaut', () => {
  it('le pilotage ouvre sur le tableau de bord (D-20)', () => {
    expect(destinationParDefaut('pilotage')).toBe('accueil')
  })

  it('la gestion ouvre sur les inscriptions', () => {
    expect(destinationParDefaut('gestion')).toBe('inscriptions')
  })

  it('l’ouverture d’un axe appartient TOUJOURS à cet axe', () => {
    // Sans ce garde, `entrerDansAxe` produirait une adresse que la validation rejette, et l'écran
    // affiché ne correspondrait pas à l'adresse — exactement ce que la validation existe pour éviter.
    for (const { axe } of AXES) {
      expect(
        AXE_PAR_DESTINATION[destinationParDefaut(axe) as keyof typeof AXE_PAR_DESTINATION],
      ).toBe(axe)
    }
  })

  it('l’atelier n’ouvre PAS sur une brique qui exige un tournoi (DETTE-023)', () => {
    // Les quatre briques FFTA réclament encore un tournoi que l'atelier ne propose pas de choisir :
    // ouvrir l'axe sur l'une d'elles afficherait un écran vide dès le premier clic.
    const bloquees: DestinationAdminId[] = ['categories', 'blasons', 'bareme', 'phases']
    expect(bloquees).not.toContain(destinationParDefaut('atelier'))
  })
})

describe('analyserSegmentsAdmin', () => {
  it('sans segment : accueil de l’admin, aucun tournoi', () => {
    expect(analyserSegmentsAdmin([])).toEqual({
      tournoiId: null,
      axe: null,
      destinationDemandee: null,
    })
  })

  it('reconnaît un axe seul', () => {
    expect(analyserSegmentsAdmin(['pilotage'])).toEqual({
      tournoiId: null,
      axe: 'pilotage',
      destinationDemandee: null,
    })
  })

  it('reconnaît tournoi + axe + destination', () => {
    expect(analyserSegmentsAdmin(['12', 'pilotage', 'supervision'])).toEqual({
      tournoiId: 12,
      axe: 'pilotage',
      destinationDemandee: 'supervision',
    })
  })

  it('le tournoi est reconnu à sa FORME, sans ambiguïté avec un axe', () => {
    // Aucun axe ni aucune destination n'est numérique : la distinction est totale.
    expect(analyserSegmentsAdmin(['atelier', 'gabarits']).tournoiId).toBeNull()
    expect(analyserSegmentsAdmin(['7']).tournoiId).toBe(7)
    expect(analyserSegmentsAdmin(['7']).axe).toBeNull()
  })

  it('un axe inconnu retombe sur l’accueil, pas sur une page vide', () => {
    expect(analyserSegmentsAdmin(['preparation', 'blasons'])).toEqual({
      tournoiId: null,
      axe: null,
      destinationDemandee: null,
    })
  })
})

describe('segmentsAdmin', () => {
  it('est la réciproque exacte d’analyserSegmentsAdmin', () => {
    const cas: [number | null, Axe | null, DestinationAdminId | null][] = [
      [null, null, null],
      [null, 'atelier', 'gabarits'],
      [12, 'pilotage', 'supervision'],
      [3, 'gestion', 'paiements'],
    ]
    for (const [tournoiId, axe, destination] of cas) {
      const segments = segmentsAdmin(tournoiId, axe, destination)
      const relu = analyserSegmentsAdmin(segments)
      expect(relu.tournoiId).toBe(tournoiId)
      expect(relu.axe).toBe(axe)
      expect(relu.destinationDemandee).toBe(axe === null ? null : destination)
    }
  })

  it('CA — le tournoi survit au changement d’écran et d’axe', () => {
    // C'est la promesse « un lien s'ouvre sur la même vue » : sans le tournoi dans l'adresse, 21
    // destinations sur 24 retombent sur « choisissez un tournoi » après un F5.
    expect(segmentsAdmin(12, 'gestion', 'inscriptions')).toEqual(['12', 'gestion', 'inscriptions'])
  })
})

describe('destinationValide', () => {
  it('accepte une destination proposée par l’axe', () => {
    expect(destinationValide('supervision', ['accueil', 'supervision'])).toBe('supervision')
  })

  it('REFUSE une destination qui appartient à un autre axe', () => {
    // Sans ce garde, /admin/atelier/supervision afficherait un écran de pilotage sous l'intitulé
    // « Atelier » — exactement le mélange que le découpage en axes supprime.
    expect(destinationValide('supervision', ['gabarits', 'clubs'])).toBeNull()
  })

  it('sans destination demandée : rien, l’axe choisira son ouverture', () => {
    expect(destinationValide(null, ['gabarits'])).toBeNull()
  })
})
