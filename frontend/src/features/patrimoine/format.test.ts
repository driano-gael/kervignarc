// Tests des mises en mots du patrimoine (E01US023) — module **pur**, sans rendu.
//
// `decrireRapport` porte trois branches de décision, dont une — « la bibliothèque est vide » — que
// la première version confondait avec « tout était déjà là ». C'est le cas de la **toute première
// utilisation** : l'organisateur assemble avant d'avoir chargé le référentiel, lit « rien de neuf »
// et repart avec un tournoi vide en croyant l'avoir garni. Ce fichier existe pour cette branche-là.

import { describe, expect, it } from 'vitest'
import type { Etape, RapportAssemblage } from './api'
import { decrireEtape, decrireRapport } from './format'

function rapport(partiel: Partial<RapportAssemblage> = {}): RapportAssemblage {
  return {
    blasons_copies: 0,
    blasons_ignores: 0,
    categories_copiees: 0,
    categories_ignorees: 0,
    ...partiel,
  }
}

describe('decrireRapport', () => {
  it('bibliothèque vide : ne dit PAS « tout était déjà là », et indique quoi faire', () => {
    const message = decrireRapport(rapport())

    expect(message).not.toContain('déjà là')
    expect(message).toContain('vide')
    expect(message).toContain('référentiel FFTA')
  })

  it('rien à copier mais des briques déjà présentes : « rien de neuf »', () => {
    const message = decrireRapport(rapport({ categories_ignorees: 32, blasons_ignores: 4 }))

    expect(message).toBe('Rien de neuf : tout était déjà là.')
  })

  it('des briques copiées : le compte des ajouts ET celui des ignorés', () => {
    const message = decrireRapport(
      rapport({
        categories_copiees: 32,
        blasons_copies: 4,
        categories_ignorees: 1,
        blasons_ignores: 2,
      }),
    )

    expect(message).toContain('32 catégorie(s)')
    expect(message).toContain('4 blason(s)')
    // Les deux familles d'ignorés sont sommées — pas seulement les catégories.
    expect(message).toContain('3 déjà présents')
  })
})

describe('decrireEtape', () => {
  function etape(partiel: Partial<Etape> = {}): Etape {
    return {
      ordre: 1,
      type: 'qualification',
      bareme: null,
      validation: null,
      big_shoot_off: null,
      suisse: null,
      colline: null,
      decoupage: null,
      profondeur: null,
      // E05US033 : les deux réglages neufs, au défaut d'avant l'US.
      arrets: [],
      poules: null,
      sources: [],
      effectif: null,
      ...partiel,
    }
  }

  it('qualification avec barème et effectif', () => {
    const texte = decrireEtape(
      etape({ bareme: { nb_volees: 20, nb_fleches_par_volee: 3 }, effectif: 16 }),
    )

    expect(texte).toBe('Qualification 20×3 (16 archers)')
  })

  it('sans barème ni effectif : le seul type, sans chiffres orphelins', () => {
    expect(decrireEtape(etape({ type: 'elimination_directe' }))).toBe('Élimination directe')
  })

  it('un effectif de zéro n’est pas confondu avec « non déclaré »', () => {
    // `effectif: 0` est refusé par le domaine (`EffectifPhaseInvalide`), mais la fonction ne doit
    // pas le traiter comme `null` : un `if (etape.effectif)` au lieu d'un `=== null` masquerait la
    // valeur au lieu de la montrer telle qu'elle est arrivée.
    expect(decrireEtape(etape({ type: 'placement', effectif: 0 }))).toContain('(0 archers)')
  })
})
