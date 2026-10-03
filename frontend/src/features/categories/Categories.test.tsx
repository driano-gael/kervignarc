// Écran des catégories en tableau, édition depuis la ligne (E00US016, CA « liste/fiche »).

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Categories } from './Categories'

const mutation = () => ({ mutate: vi.fn(), isPending: false, error: null })
const { blasons } = vi.hoisted(() => ({ blasons: { lus: true } }))

vi.mock('./hooks', () => ({
  useCategories: () => ({
    isError: false,
    data: [
      {
        id: 1,
        tournoi_id: 1,
        libelle: 'Senior Homme Classique',
        arme: 'classique',
        ages: ['S1', 'S2'],
        sexe: 'H',
        blason_id: 4,
        hauteur_cm: 130,
      },
      {
        id: 2,
        tournoi_id: 1,
        libelle: 'Découverte',
        arme: null,
        ages: [],
        sexe: null,
        blason_id: null,
        hauteur_cm: 110,
      },
    ],
  }),
  useCreerCategorie: () => mutation(),
  useModifierCategorie: () => mutation(),
  useSupprimerCategorie: () => mutation(),
}))

vi.mock('../blasons/hooks', () => ({
  useBlasons: () => ({ data: blasons.lus ? [{ id: 4, nom: 'Trispot 40' }] : undefined }),
}))

// La ligne dont la 1ʳᵉ cellule porte ce libellé ; échoue en clair si elle n'existe pas.
const ligneDe = (libelle: string) => {
  const ligne = within(screen.getByRole('table'))
    .getAllByRole('row')
    .find((tr) => within(tr).queryByRole('cell', { name: libelle }) !== null)
  if (ligne === undefined) throw new Error(`aucune ligne « ${libelle} »`)
  return ligne
}

const cellulesDe = (libelle: string) =>
  within(ligneDe(libelle))
    .getAllByRole('cell')
    .map((td) => td.textContent)

describe('Catégories — tableau', () => {
  it('donne une colonne à chaque attribut, blason nommé', () => {
    render(<Categories tournoiId={1} />)

    expect(
      within(screen.getByRole('table'))
        .getAllByRole('columnheader')
        .map((th) => th.textContent),
    ).toEqual([
      'Libellé',
      'Arme',
      'Tranches d’âge',
      'Sexe',
      'Blason par défaut',
      'Centre',
      'Actions',
    ])
    expect(cellulesDe('Senior Homme Classique').slice(0, 6)).toEqual([
      'Senior Homme Classique',
      'classique',
      'S1, S2',
      'Homme',
      'Trispot 40',
      '130 cm',
    ])
  })

  it('marque d’un tiret un attribut absent, plutôt qu’une cellule vide', () => {
    render(<Categories tournoiId={1} />)

    expect(cellulesDe('Découverte').slice(1, 5)).toEqual(['—', '—', '—', '—'])
  })

  it('ne dit pas « aucun blason » tant que les blasons ne sont pas lus', () => {
    blasons.lus = false
    try {
      render(<Categories tournoiId={1} />)
      expect(cellulesDe('Senior Homme Classique')[4]).toBe('…')
      expect(cellulesDe('Découverte')[4]).toBe('—')
    } finally {
      blasons.lus = true
    }
  })

  it('« Éditer » remplace la ligne par le formulaire pré-rempli', async () => {
    render(<Categories tournoiId={1} />)

    await userEvent.click(screen.getByRole('button', { name: 'Éditer Découverte' }))

    expect(within(screen.getByRole('table')).getByLabelText('Libellé de la catégorie')).toHaveValue(
      'Découverte',
    )
  })
})
