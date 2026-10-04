// L'aide du barème des derniers tours ne parle de petite finale que là où elle existe : au tableau.

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { presetClub } from './baremeDuel'
import type { TypePhase } from './catalogue'
import { ReglageBaremeDuel } from './ReglageBaremeDuel'

function monter(type: TypePhase) {
  render(
    <ReglageBaremeDuel
      etat={presetClub(['Arc Classique'])}
      surChangement={() => {}}
      armes={['Arc Classique']}
      sourceArmes="tournoi"
      type={type}
    />,
  )
}

describe('ReglageBaremeDuel — aide des derniers tours (E01US027, CA 3)', () => {
  it('au tableau, la petite finale suit les derniers tours', () => {
    monter('elimination_directe')
    expect(screen.getByText(/petite finale/)).toBeInTheDocument()
  })

  it.each<TypePhase>(['poules', 'suisse', 'colline'])(
    'en %s, aucune petite finale n’est promise',
    (type) => {
      monter(type)
      expect(screen.getByText(/^Concerne /)).toBeInTheDocument()
      expect(screen.queryByText(/petite finale/)).not.toBeInTheDocument()
    },
  )
})
