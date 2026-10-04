// Non-régression E00US024 : l'oracle est le panneau de simulation avant l'extraction.

import { describe, expect, it } from 'vitest'

import type { Bloc } from '../../shared/schema-braquets/modele'
import { EFFECTIF_MAX, type Diagnostic, type LigneClassement, type PhaseSimulee } from './api'
import {
  analyserEffectif,
  classementAffiche,
  CLASSEMENT_AFFICHE_MAX,
  compteurAffiche,
  motifEmpechementSimulation,
  noteDEcart,
} from './simulation'

describe('analyserEffectif', () => {
  it('lit un entier positif jusqu’à la borne serveur incluse', () => {
    expect(analyserEffectif('1')).toBe(1)
    expect(analyserEffectif(String(EFFECTIF_MAX))).toBe(EFFECTIF_MAX)
  })

  it('rend null au-delà de la borne, vide ou illisible', () => {
    expect(analyserEffectif(String(EFFECTIF_MAX + 1))).toBeNull()
    expect(analyserEffectif('')).toBeNull()
    expect(analyserEffectif('abc')).toBeNull()
    expect(analyserEffectif('0')).toBeNull()
  })
})

function bloc(type: Bloc['type']): Bloc {
  return {
    ordre: 1,
    type,
    effectif: null,
    tranche: null,
    nb_volees: null,
    nb_fleches_par_volee: null,
    tours: [],
    entrees: [],
    sorties: [],
    sans_suite: null,
  }
}

function diagnostic(surcharge: Partial<Diagnostic> = {}): Diagnostic {
  return {
    effectif: 64,
    applicable: true,
    blocs: [bloc('qualification')],
    anomalies: [],
    effectif_minimum: 1,
    ...surcharge,
  }
}

describe('motifEmpechementSimulation', () => {
  it('offre la simulation d’un format applicable, qualifié, à effectif valide', () => {
    expect(motifEmpechementSimulation(diagnostic(), 2)).toBeNull()
    expect(motifEmpechementSimulation(diagnostic(), EFFECTIF_MAX)).toBeNull()
  })

  it('attend le diagnostic en premier, quel que soit l’effectif', () => {
    expect(motifEmpechementSimulation(undefined, null)).toBe('Le déroulé est en cours de calcul.')
  })

  it('refuse un déroulé non applicable avant de regarder la qualification', () => {
    expect(motifEmpechementSimulation(diagnostic({ applicable: false, blocs: [] }), 10)).toMatch(
      /^On ne simule pas un déroulé/,
    )
  })

  it('refuse un format sans qualification', () => {
    expect(
      motifEmpechementSimulation(diagnostic({ blocs: [bloc('elimination_directe')] }), 10),
    ).toMatch(/^Ce format ne décrit aucune qualification/)
  })

  it('refuse un effectif absent ou hors de 2..EFFECTIF_MAX', () => {
    const attendu = `Indiquez un effectif entre 2 et ${EFFECTIF_MAX} archers pour lancer la simulation.`
    expect(motifEmpechementSimulation(diagnostic(), null)).toBe(attendu)
    expect(motifEmpechementSimulation(diagnostic(), 1)).toBe(attendu)
    expect(motifEmpechementSimulation(diagnostic(), EFFECTIF_MAX + 1)).toBe(attendu)
  })
})

function phase(surcharge: Partial<PhaseSimulee> = {}): PhaseSimulee {
  return {
    ordre: 1,
    type: 'elimination_directe',
    effectif: 32,
    effectif_projete: 32,
    ecart: false,
    joue: true,
    tours: 5,
    tours_projetes: 5,
    duels: 31,
    duels_projetes: 31,
    ...surcharge,
  }
}

describe('noteDEcart', () => {
  it('ne dit rien d’une phase jouée comme annoncé', () => {
    expect(noteDEcart(phase())).toBeNull()
  })

  it('distingue la simulation qui ne sait pas jouer d’un moteur qui ne sait pas dérouler', () => {
    expect(noteDEcart(phase({ type: 'poules', joue: false }))).toMatch(
      /^▲ la simulation ne sait pas encore jouer/,
    )
    expect(noteDEcart(phase({ type: 'placement', joue: false }))).toMatch(
      /^▲ le moteur ne sait pas encore dérouler/,
    )
  })

  it('prime l’absence de jeu sur l’écart', () => {
    expect(noteDEcart(phase({ type: 'barrage', joue: false, ecart: true }))).toMatch(/^▲ le moteur/)
  })

  it('rappelle ce que le schéma annonçait, inconnu rendu « — »', () => {
    expect(noteDEcart(phase({ ecart: true, effectif_projete: 16 }))).toBe(
      '▲ le schéma annonçait 16 archers, 5 tours et 31 duels',
    )
    expect(noteDEcart(phase({ ecart: true, tours_projetes: null, duels_projetes: null }))).toBe(
      '▲ le schéma annonçait 32 archers, — tours et — duels',
    )
  })

  it('rend un effectif projeté inconnu par du vide, comme le faisait le rendu JSX', () => {
    expect(noteDEcart(phase({ ecart: true, effectif_projete: null }))).toBe(
      '▲ le schéma annonçait  archers, 5 tours et 31 duels',
    )
  })
})

describe('compteurAffiche', () => {
  it('affiche un compteur positif d’une phase jouée', () => {
    expect(compteurAffiche(true, 1)).toBe(1)
  })

  it('rend « — » pour zéro ou pour une phase non jouée', () => {
    expect(compteurAffiche(true, 0)).toBe('—')
    expect(compteurAffiche(false, 7)).toBe('—')
  })
})

describe('classementAffiche', () => {
  function classement(n: number): LigneClassement[] {
    return Array.from({ length: n }, (_, i) => ({
      rang: i + 1,
      nom: `N${i}`,
      prenom: 'P',
      total: 600 - i,
    }))
  }

  it('montre tout jusqu’au plafond inclus', () => {
    expect(classementAffiche([])).toEqual({ lignes: [], tronque: false })
    const plein = classementAffiche(classement(CLASSEMENT_AFFICHE_MAX))
    expect(plein.lignes).toHaveLength(CLASSEMENT_AFFICHE_MAX)
    expect(plein.tronque).toBe(false)
  })

  it('tronque au plafond au-delà, en gardant la tête', () => {
    const tronque = classementAffiche(classement(CLASSEMENT_AFFICHE_MAX + 1))
    expect(tronque.tronque).toBe(true)
    expect(tronque.lignes).toHaveLength(CLASSEMENT_AFFICHE_MAX)
    expect(tronque.lignes[0]!.rang).toBe(1)
  })

  it('plafonne à 32 lignes', () => {
    expect(CLASSEMENT_AFFICHE_MAX).toBe(32)
  })
})
