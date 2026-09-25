// Tests de **montage** du plan de cibles public — P04, variante retenue au questionnaire du 04/08 :
// « Ma cible d'abord, plan ensuite » (✅ validé tel quel). E17US009. La règle d'ordre vit dans
// `mesPlaces` (testée en node) ; ici, l'**assemblage** : la carte vient avant la grille.

import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useArchers } from '../archers/hooks'
import { useDeparts } from '../departs/hooks'
import { usePlanDeCibles } from './hooks'
import { PlanCiblesPublic } from './PlanCiblesPublic'

vi.mock('../archers/hooks', () => ({ useArchers: vi.fn() }))
vi.mock('../departs/hooks', () => ({ useDeparts: vi.fn() }))
vi.mock('./hooks', () => ({ usePlanDeCibles: vi.fn() }))

// Retours de React Query réduits aux champs lus : double de test assumé (règle 4-front).
const resultat = (patch: Record<string, unknown>) => patch as never

const placement = (position: string, archer_id: number) => ({
  position,
  archer_id,
  blason_id: 1,
  inscription_id: archer_id * 10,
})

describe('PlanCiblesPublic — ma cible d’abord', () => {
  beforeEach(() => {
    vi.mocked(useDeparts).mockReturnValue(
      resultat({
        data: [{ id: 10, numero: 1, horaire: null, etat: 'ouvert' }],
        isPending: false,
        isError: false,
      }),
    )
    vi.mocked(useArchers).mockReturnValue(
      resultat({
        data: [
          { id: 7, prenom: 'Paul', nom: 'MARTIN' },
          { id: 8, prenom: 'Jean', nom: 'DURAND' },
        ],
      }),
    )
    vi.mocked(usePlanDeCibles).mockReturnValue(
      resultat({
        data: {
          depart_id: 10,
          conflits: [],
          cibles: [
            { index: 3, capacite: 4, placements: [placement('A', 8)] },
            { index: 12, capacite: 4, placements: [placement('B', 7)] },
          ],
        },
        isPending: false,
        isError: false,
      }),
    )
  })

  it('la place de l’archer suivi précède la grille, et sa cible y est marquée', () => {
    const { container } = render(<PlanCiblesPublic tournoiId={1} suivis={[7]} />)

    const carte = screen.getByRole('list', { name: 'Vos archers sur ce départ' })
    expect(within(carte).getByText('Cible 12 · couloir B')).toBeInTheDocument()
    const grille = container.querySelector('.plan-public')
    expect(grille).not.toBeNull()
    // La carte est **avant** la grille dans l'ordre du document — c'est tout le parti pris.
    expect(carte.compareDocumentPosition(grille as Node) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
    expect(within(grille as HTMLElement).getAllByText('vos archers')).toHaveLength(1)
  })

  it('sans archer suivi, le plan reste seul — ni carte, ni marque', () => {
    render(<PlanCiblesPublic tournoiId={1} />)

    expect(screen.queryByRole('list', { name: 'Vos archers sur ce départ' })).toBeNull()
    expect(screen.queryByText('vos archers')).toBeNull()
  })
})
