// Le réglage « par équipes » dans l'atelier « Composer un format » (E13US004, CA 1, versant
// bibliothèque). Pendant de `phases/Equipes.test.tsx` : les deux formulaires sont jumeaux (DETTE-080).

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { Etape } from '../patrimoine/api'
import { FormulaireEtape } from './Deroule'

const TABLEAU: Etape = {
  ordre: 2,
  type: 'elimination_directe',
  bareme: null,
  validation: null,
  poules: null,
  big_shoot_off: null,
  suisse: null,
  bareme_duel: null,
  equipes: null,
  colline: null,
  decoupage: null,
  sources: [],
  effectif: null,
  profondeur: null,
  arrets: [],
  titre: null,
  duree_prevue: null,
}

function poser(etape: Etape) {
  const surValider = vi.fn()
  render(
    <FormulaireEtape
      armes={[]}
      etape={etape}
      etapesAmont={[]}
      surValider={surValider}
      surAnnuler={() => {}}
    />,
  )
  return surValider
}

describe('le réglage « par équipes » dans l’atelier de composition', () => {
  it('part avec l’étape, et se relit', async () => {
    const surValider = poser(TABLEAU)

    await userEvent.selectOptions(screen.getByLabelText(/Participants/), 'mixte')
    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))

    expect(surValider).toHaveBeenLastCalledWith(expect.objectContaining({ equipes: 'mixte' }))
  })

  it('un réglage existant est réémis quand on enregistre autre chose', async () => {
    const surValider = poser({ ...TABLEAU, equipes: 'standard' })

    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))

    expect(surValider).toHaveBeenCalledWith(expect.objectContaining({ equipes: 'standard' }))
  })

  it('retyper l’étape hors élimination directe efface le réglage', async () => {
    const surValider = poser({ ...TABLEAU, equipes: 'standard' })

    await userEvent.selectOptions(screen.getByLabelText(/Type/), 'poules')
    expect(screen.queryByLabelText(/Participants/)).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))

    expect(surValider).toHaveBeenLastCalledWith(expect.objectContaining({ equipes: null }))
  })
})
