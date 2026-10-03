// Écran des clubs en tableau, édition depuis la ligne (E00US016, CA « liste/fiche »).

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Clubs } from './Clubs'

const mutation = () => ({ mutate: vi.fn(), isPending: false, error: null })
const { supprimer } = vi.hoisted(() => ({ supprimer: vi.fn() }))

vi.mock('./hooks', () => ({
  useClubs: () => ({
    isError: false,
    data: [
      { id: 1, nom: 'Arc Fougerais' },
      { id: 2, nom: 'Archers de Vitré' },
    ],
  }),
  useCreerClub: () => mutation(),
  useModifierClub: () => mutation(),
  useSupprimerClub: () => ({ mutate: supprimer, isPending: false, error: null }),
}))

describe('Clubs — tableau', () => {
  it('liste les clubs dans un tableau à colonnes nommées', () => {
    render(<Clubs ouvrir={null} onOuvrir={vi.fn()} />)

    const tableau = screen.getByRole('table')
    expect(
      within(tableau)
        .getAllByRole('columnheader')
        .map((th) => th.textContent),
    ).toEqual(['Nom', 'Actions'])
    expect(within(tableau).getByRole('cell', { name: 'Archers de Vitré' })).toBeInTheDocument()
  })

  it('le club ouvert par l’adresse s’édite à la place de sa ligne', () => {
    render(<Clubs ouvrir={2} onOuvrir={vi.fn()} />)

    const tableau = screen.getByRole('table')
    expect(within(tableau).getByLabelText('Nom du club')).toHaveValue('Archers de Vitré')
    expect(within(tableau).getByRole('cell', { name: 'Arc Fougerais' })).toBeInTheDocument()
  })

  it('chaque action nomme son club, et la suppression attend la confirmation', async () => {
    render(<Clubs ouvrir={null} onOuvrir={vi.fn()} />)

    await userEvent.click(screen.getByRole('button', { name: 'Supprimer Arc Fougerais' }))
    expect(supprimer).not.toHaveBeenCalled()
    await userEvent.click(
      screen.getByRole('button', { name: 'Confirmer la suppression de Arc Fougerais' }),
    )
    expect(supprimer).toHaveBeenCalledWith(1)
  })
})
