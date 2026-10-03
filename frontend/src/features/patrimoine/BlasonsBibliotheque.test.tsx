// Taille d'un blason du club en fractions (E00US016, CA « fractions de blason en déroulante ») :
// la bibliothèque est l'autre formulaire où un blason se crée (E01US023).

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { BlasonsBibliotheque } from './Bibliotheque'

const mutation = () => ({ mutate: vi.fn(), isPending: false, error: null })
const { creer } = vi.hoisted(() => ({ creer: vi.fn() }))

vi.mock('./hooks', () => ({
  useBlasonsBibliotheque: () => ({
    isError: false,
    isPending: false,
    data: [
      {
        id: 1,
        tournoi_id: null,
        nom: 'Trispot 40',
        taille: 0.5,
        capacite: 1,
        zones: ['10', 'M'],
        origine: 'ffta',
      },
    ],
  }),
  useCreerBlasonBibliotheque: () => ({ mutate: creer, isPending: false, error: null }),
  useDupliquerBlasonBibliotheque: () => mutation(),
  useSupprimerBlasonBibliotheque: () => mutation(),
  usePrechargerFftaBibliotheque: () => mutation(),
  useCategoriesBibliotheque: () => ({ isError: false, isPending: false, data: [] }),
  useCreerCategorieBibliotheque: () => mutation(),
  useDupliquerCategorieBibliotheque: () => mutation(),
  useRenommerCategorieBibliotheque: () => mutation(),
  useSupprimerCategorieBibliotheque: () => mutation(),
}))

const champTaille = () => screen.getByLabelText('Place occupée sur une cible')

describe('Blasons du club — taille en fractions', () => {
  it('affiche la taille d’un blason en fraction', () => {
    render(<BlasonsBibliotheque />)
    expect(screen.getByText(/taille ½/)).toBeInTheDocument()
  })

  it('crée un blason au tiers exact', async () => {
    creer.mockClear()
    render(<BlasonsBibliotheque />)

    await userEvent.type(screen.getByLabelText('Nom du blason'), 'Trispot 60')
    await userEvent.selectOptions(champTaille(), 'Tiers (⅓)')
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter au club' }))

    expect(creer).toHaveBeenCalledWith(
      { nom: 'Trispot 60', taille: 1 / 3, capacite: 1 },
      expect.anything(),
    )
  })

  it('« Autre… » déplie un réel libre, exigé avant l’envoi', async () => {
    render(<BlasonsBibliotheque />)
    await userEvent.type(screen.getByLabelText('Nom du blason'), 'Maison')
    expect(
      screen.queryByLabelText('Autre place occupée sur une cible (réel de 0 à 1)'),
    ).not.toBeInTheDocument()

    await userEvent.selectOptions(champTaille(), 'Autre…')

    expect(
      screen.getByLabelText('Autre place occupée sur une cible (réel de 0 à 1)'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ajouter au club' })).toBeDisabled()
  })
})
