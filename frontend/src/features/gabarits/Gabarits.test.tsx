// Écran des gabarits en tableau, édition depuis la ligne (E00US016, CA « liste/fiche »).

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Gabarits } from './Gabarits'

const mutation = () => ({ mutate: vi.fn(), isPending: false, error: null })

vi.mock('./hooks', () => ({
  useGabarits: () => ({
    isError: false,
    data: [
      {
        id: 7,
        nom: 'Salle municipale',
        nb_cibles: 2,
        tournoi_id: null,
        cibles: [
          { index: 1, capacite: 4, positions: ['A', 'B', 'C', 'D'] },
          { index: 2, capacite: 2, positions: ['A', 'B'] },
        ],
      },
    ],
  }),
  useCreerGabarit: () => mutation(),
  useModifierGabarit: () => mutation(),
  useSupprimerGabarit: () => mutation(),
}))

describe('Gabarits — tableau', () => {
  it('sépare cibles et couloirs en colonnes', () => {
    render(<Gabarits />)

    const tableau = screen.getByRole('table')
    expect(
      within(tableau)
        .getAllByRole('columnheader')
        .map((th) => th.textContent),
    ).toEqual(['Nom', 'Cibles', 'Couloirs de tir', 'Actions'])
    const cellules = within(tableau)
      .getAllByRole('cell')
      .map((td) => td.textContent)
    expect(cellules.slice(0, 3)).toEqual(['Salle municipale', '2', "jusqu'à 2/4 couloirs/cible"])
  })

  it('« Éditer » remplace la ligne par le formulaire pré-rempli', async () => {
    render(<Gabarits />)

    await userEvent.click(screen.getByRole('button', { name: 'Éditer Salle municipale' }))

    const tableau = screen.getByRole('table')
    expect(within(tableau).getByLabelText('Nom du gabarit')).toHaveValue('Salle municipale')
    expect(within(tableau).getByLabelText('Nombre de cibles')).toHaveValue(2)
  })
})
