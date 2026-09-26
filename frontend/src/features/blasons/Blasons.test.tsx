// Montage de l'écran des blasons — A06, variante B retenue le 04/08 : « la liste reste, l'édition
// s'ouvre à droite ». La variante A, écartée, remplaçait la ligne par le formulaire. E17US007.

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Blasons } from './Blasons'

const mutation = () => ({ mutate: vi.fn(), isPending: false, error: null })
// `vi.hoisted` : la fabrique de `vi.mock` est remontée en tête de fichier, avant toute déclaration.
const { supprimer, etat } = vi.hoisted(() => ({ supprimer: vi.fn(), etat: { lue: true } }))

vi.mock('./hooks', () => ({
  useBlasons: () =>
    etat.lue
      ? { isError: false, isSuccess: true, data: LISTE }
      : { isError: false, isSuccess: false, data: undefined },
  useCreerBlason: () => mutation(),
  useModifierBlason: () => mutation(),
  useSupprimerBlason: () => ({ mutate: supprimer, isPending: false, error: null }),
}))

const LISTE = [
  {
    id: 1,
    tournoi_id: 1,
    nom: 'Trispot 40',
    taille: 0.5,
    capacite: 1,
    zones: ['10', 'M'],
    origine: 'ffta',
  },
  {
    id: 2,
    tournoi_id: 1,
    nom: 'Mono maison',
    taille: 1,
    capacite: 2,
    zones: ['10', '9', 'M'],
    origine: 'utilisateur',
  },
]

describe('Blasons — liste et panneau latéral', () => {
  it('choisir une ligne ouvre le panneau pré-rempli, et la liste reste à l’écran', async () => {
    render(<Blasons tournoiId={1} />)

    await userEvent.click(screen.getByRole('button', { name: 'Mono maison' }))

    const panneau = screen.getByRole('complementary', { name: 'Édition du blason' })
    expect(within(panneau).getByLabelText('Nom du blason')).toHaveValue('Mono maison')
    // La liste n'a pas été remplacée : l'autre blason est toujours là, dans le tableau.
    expect(
      within(screen.getByRole('table')).getByRole('button', { name: 'Trispot 40' }),
    ).toBeInTheDocument()
  })

  it('sépare le référentiel FFTA des créations de l’organisation', () => {
    render(<Blasons tournoiId={1} />)

    const groupes = screen.getAllByRole('rowheader').map((th) => th.textContent)
    expect(groupes).toEqual(['Référentiel FFTA', 'Créés par l’organisation'])
  })

  // Revue, axe B : l'arbitrage « la suppression passe dans le panneau, avec sa confirmation » (Notes
  // d'E17US007) n'avait pas de test.
  it('supprimer passe par le panneau, et n’agit qu’à la confirmation', async () => {
    render(<Blasons tournoiId={1} />)
    await userEvent.click(screen.getByRole('button', { name: 'Mono maison' }))

    await userEvent.click(screen.getByRole('button', { name: 'Supprimer ce blason' }))
    expect(supprimer).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'Confirmer la suppression' }))
    expect(supprimer).toHaveBeenCalledWith(2, expect.anything())
  })

  // 2ᵉ passe, axe B : « 0 blason » annoncé avant que la liste soit lue.
  it('le compte n’apparaît qu’une fois la liste lue', () => {
    etat.lue = false
    const { container, unmount } = render(<Blasons tournoiId={1} />)
    expect(container.querySelector('.blasons__compte')?.textContent).toBe('')
    unmount()

    etat.lue = true
    const lue = render(<Blasons tournoiId={1} />)
    expect(lue.container.querySelector('.blasons__compte')?.textContent).toBe('2 blasons')
  })
})
