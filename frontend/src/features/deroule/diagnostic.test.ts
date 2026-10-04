// Non-régression E00US024 : l'oracle est l'affichage du diagnostic avant l'extraction.

import { describe, expect, it } from 'vitest'

import type { Bloc, Flux } from '../../shared/schema-braquets/modele'
import type { Anomalie, Diagnostic } from './api'
import { constatEffectifMinimum, intituleAnomalie, motifsDeReserve } from './diagnostic'

function flux(nature: Flux['nature']): Flux {
  return {
    ordre_source: 1,
    ordre_cible: 2,
    nature,
    effectif: 8,
    rang_debut: 1,
    rang_fin: 8,
    tour: null,
    issue: null,
  }
}

function bloc(type: Bloc['type'], entrees: Flux[] = []): Bloc {
  return {
    ordre: 2,
    type,
    effectif: 8,
    tranche: null,
    nb_volees: null,
    nb_fleches_par_volee: null,
    tours: [],
    entrees,
    sorties: [],
    sans_suite: 0,
  }
}

function diagnostic(surcharge: Partial<Diagnostic> = {}): Diagnostic {
  return {
    effectif: null,
    applicable: true,
    blocs: [],
    anomalies: [],
    effectif_minimum: 1,
    ...surcharge,
  }
}

describe('constatEffectifMinimum', () => {
  it('ne dit rien d’un minimum trivial (1 ou moins)', () => {
    expect(constatEffectifMinimum(diagnostic({ effectif_minimum: 1, effectif: 0 }))).toBeNull()
    expect(constatEffectifMinimum(diagnostic({ effectif_minimum: 0 }))).toBeNull()
  })

  it('informe sans effectif simulé', () => {
    expect(constatEffectifMinimum(diagnostic({ effectif_minimum: 2 }))).toEqual({
      regime: 'information',
      minimum: 2,
    })
  })

  it('informe quand l’effectif simulé atteint pile le minimum', () => {
    expect(constatEffectifMinimum(diagnostic({ effectif_minimum: 40, effectif: 40 }))).toEqual({
      regime: 'information',
      minimum: 40,
    })
  })

  it('avertit quand l’effectif simulé passe sous le minimum', () => {
    expect(constatEffectifMinimum(diagnostic({ effectif_minimum: 40, effectif: 39 }))).toEqual({
      regime: 'insuffisant',
      minimum: 40,
      effectif: 39,
    })
  })
})

describe('motifsDeReserve', () => {
  it('ne réserve rien d’un déroulé vide ou entièrement par rangs', () => {
    expect(motifsDeReserve(diagnostic())).toBeNull()
    expect(
      motifsDeReserve(
        diagnostic({
          blocs: [bloc('qualification'), bloc('elimination_directe', [flux('rangs')])],
        }),
      ),
    ).toBeNull()
  })

  it('relève un prélèvement inerte (« le reste » ou issue de tour)', () => {
    expect(
      motifsDeReserve(diagnostic({ blocs: [bloc('elimination_directe', [flux('reste')])] })),
    ).toEqual({ prelevementInerte: true, libellesEnEcart: [] })
    expect(
      motifsDeReserve(
        diagnostic({
          blocs: [bloc('elimination_directe', [flux('rangs'), flux('issue_de_tour')])],
        }),
      )?.prelevementInerte,
    ).toBe(true)
  })

  it('nomme les seuls types en écart réellement présents, une fois chacun', () => {
    const motifs = motifsDeReserve(
      diagnostic({
        blocs: [bloc('qualification'), bloc('placement'), bloc('placement'), bloc('barrage')],
      }),
    )
    expect(motifs).toEqual({ prelevementInerte: false, libellesEnEcart: ['Placement', 'Barrage'] })
  })

  it('ne compte pas en écart un type que le moteur déroule', () => {
    expect(motifsDeReserve(diagnostic({ blocs: [bloc('poules'), bloc('suisse')] }))).toBeNull()
  })
})

describe('intituleAnomalie', () => {
  function anomalie(gravite: Anomalie['gravite'], ordre: number | null): Anomalie {
    return { code: 'x', message: 'm', gravite, ordre }
  }

  it('marque une anomalie bloquante localisée', () => {
    expect(intituleAnomalie(anomalie('bloquante', 2))).toEqual({
      pastille: '●',
      intitule: 'Bloquant — phase 2',
    })
  })

  it('marque un avertissement de la séquence entière, sans phase', () => {
    expect(intituleAnomalie(anomalie('avertissement', null))).toEqual({
      pastille: '▲',
      intitule: 'À vérifier',
    })
  })
})
