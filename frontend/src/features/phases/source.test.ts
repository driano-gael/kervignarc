import { describe, expect, it } from 'vitest'
import type { SourcePhase } from './api'
import { decrireSource, decrireSources, editableIci } from './source'

function source(partiel: Partial<SourcePhase> = {}): SourcePhase {
  return {
    ordre_source: 1,
    nature: 'rangs',
    rang_debut: 1,
    rang_fin: 32,
    tour: null,
    issue: null,
    ...partiel,
  }
}

describe('decrireSource', () => {
  it('décrit une plage bornée', () => {
    expect(decrireSource(source())).toBe('rangs 1 à 32 de la phase 1')
  })

  it('décrit une fin ouverte par « et suivants »', () => {
    // Surface visible du CA « plages relatives » : un format prévu pour 120 tient à 82.
    expect(decrireSource(source({ rang_debut: 33, rang_fin: null }))).toBe(
      'rangs 33 et suivants de la phase 1',
    )
  })

  it('décrit « le reste »', () => {
    expect(decrireSource(source({ nature: 'reste', rang_fin: null }))).toBe(
      'le reste de la phase 1',
    )
  })

  it('décrit les gagnants d’un tour', () => {
    expect(
      decrireSource(
        source({ nature: 'issue_de_tour', rang_fin: null, tour: 2, issue: 'gagnants' }),
      ),
    ).toBe('gagnants du tour 2 de la phase 1')
  })

  it('décrit les perdants d’un tour', () => {
    expect(
      decrireSource(
        source({
          ordre_source: 3,
          nature: 'issue_de_tour',
          rang_fin: null,
          tour: 3,
          issue: 'perdants',
        }),
      ),
    ).toBe('perdants du tour 3 de la phase 3')
  })
})

describe('decrireSources', () => {
  it('annonce les inscriptions quand la phase n’a aucun prélèvement', () => {
    expect(decrireSources([])).toBe('alimentée par les inscriptions')
  })

  it('enchaîne plusieurs prélèvements de natures différentes', () => {
    // L'exemple du commanditaire : les demi-finalistes d'un tableau, et le reste d'un autre.
    const composition = [
      source({
        ordre_source: 2,
        nature: 'issue_de_tour',
        rang_fin: null,
        tour: 3,
        issue: 'perdants',
      }),
      source({ nature: 'reste', rang_fin: null }),
    ]
    expect(decrireSources(composition)).toBe(
      'perdants du tour 3 de la phase 2, puis le reste de la phase 1',
    )
  })
})

describe('editableIci', () => {
  it('accepte une phase sans prélèvement', () => {
    expect(editableIci([])).toBe(true)
  })

  it('accepte un prélèvement unique par rangs, fin ouverte comprise', () => {
    expect(editableIci([source()])).toBe(true)
    expect(editableIci([source({ rang_fin: null })])).toBe(true)
  })

  it('refuse une phase à plusieurs prélèvements', () => {
    // Le formulaire n'en décrit qu'un : le soumettre effacerait le second sans le dire.
    expect(editableIci([source(), source({ rang_debut: 33, rang_fin: 64 })])).toBe(false)
  })

  it('refuse une nature que le formulaire n’expose pas', () => {
    expect(editableIci([source({ nature: 'reste', rang_fin: null })])).toBe(false)
    expect(
      editableIci([
        source({ nature: 'issue_de_tour', rang_fin: null, tour: 2, issue: 'gagnants' }),
      ]),
    ).toBe(false)
  })
})
