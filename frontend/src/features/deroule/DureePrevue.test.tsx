// La **durée prévue** d'une étape dans l'atelier « Composer un format » (E03US010, CA 8).
//
// L'atelier `PUT` le format entier : un formulaire qui ne renverrait pas la durée l'effacerait.

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
  colline: null,
  decoupage: null,
  sources: [],
  effectif: null,
  profondeur: null,
  arrets: [],
  titre: null,
  duree_prevue: 45,
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

describe('la durée prévue dans l’atelier de composition', () => {
  it('est réémise telle quelle quand on enregistre autre chose', async () => {
    const surValider = poser(TABLEAU)

    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))

    expect(surValider).toHaveBeenCalledWith(expect.objectContaining({ duree_prevue: 45 }))
  })

  it('se modifie et se retire', async () => {
    const surValider = poser(TABLEAU)
    const champ = screen.getByLabelText(/Durée prévue/)

    await userEvent.clear(champ)
    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))
    expect(surValider).toHaveBeenLastCalledWith(expect.objectContaining({ duree_prevue: null }))

    await userEvent.type(champ, '90')
    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))
    expect(surValider).toHaveBeenLastCalledWith(expect.objectContaining({ duree_prevue: 90 }))
  })
})
