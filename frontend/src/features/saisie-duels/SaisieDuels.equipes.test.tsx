// L'écran des duels d'un tableau d'équipes (E13US004, CA 2 et 7) : chaque camp se nomme par son
// équipe et ses membres, et les équipes qui n'entrent pas sont listées avec leurs motifs.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Duel, Tableau } from './api'
import { SaisieDuels } from './SaisieDuels'

const PHASE = { id: 901, ordre: 2, type: 'elimination_directe' }

const DUEL: Duel = {
  numero: 1,
  tour: 1,
  place_en_jeu: [1, 2],
  haut: {
    archer_id: null,
    nom: 'Kervignac 1',
    prenom: '',
    equipe_id: 7,
    membres: ['Luc MARTIN', 'Anne DURAND', 'Paul ROUX'],
  },
  bas: { archer_id: null, nom: 'Lorient', prenom: '', equipe_id: 8, membres: [] },
  est_bye: false,
  mode: 'sets',
  nb_manches: 4,
  nb_fleches_par_volee: 6,
  points_pour_gagner: 5,
  nb_fleches_barrage: 3,
  zones: ['10', '9', '8', 'M'],
  validee_par: null,
  manches: [],
  barrage: null,
  resultat: null,
}

const TABLEAU: Tableau = {
  effectif: 2,
  taille: 2,
  nb_tours: 1,
  est_termine: false,
  duels: [DUEL],
  podium: [],
  equipes_ecartees: [
    {
      equipe_id: 9,
      nom: 'Hennebont',
      ecarts: ['effectif_insuffisant'],
      membres_hors_course: ['Jean PETIT'],
    },
  ],
}

let tableauCourant: Tableau = TABLEAU

afterEach(() => {
  tableauCourant = TABLEAU
})

const MUTATION = { mutate: vi.fn(), isPending: false, isError: false, error: null }

vi.mock('./hooks', () => ({
  usePhases: () => ({ data: [PHASE], isError: false, isSuccess: true, error: null }),
  useTableau: () => ({ isPending: false, isError: false, data: tableauCourant, error: null }),
  useDuel: () => ({ isPending: true, isError: false, isSuccess: false, data: undefined }),
  useDuelsEnAttente: () => 0,
  useRejeuDuelsHorsLigne: () => undefined,
  useSaisirManche: () => MUTATION,
  useSaisirBarrage: () => MUTATION,
  useValiderDuel: () => MUTATION,
}))
vi.mock('../departs/hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/hooks')>()),
  useDeparts: () => ({ data: [{ id: 41, numero: 1, statut: 'en_cours' }] }),
}))

vi.mock('../routage/hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../routage/hooks')>()),
  useRoutage: () => ({
    data: { phase_id: 901, archers: [], avis_permanent: false },
    isLoading: false,
    isError: false,
    error: null,
  }),
}))

async function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<SaisieDuels tournoiId={1} departId={41} />, { wrapper: Enveloppe })
  await userEvent.selectOptions(
    screen.getByRole('combobox', { name: 'Phase de tableau à scorer' }),
    String(PHASE.id),
  )
}

describe('SaisieDuels — un tableau d’équipes', () => {
  it('nomme chaque camp par son équipe et ses membres', async () => {
    await monter()

    expect(
      await screen.findByText('Kervignac 1 (Luc MARTIN, Anne DURAND, Paul ROUX)'),
    ).toBeInTheDocument()
    expect(screen.getByText('Lorient')).toBeInTheDocument()
  })

  it('liste les équipes non engagées avec leurs motifs', async () => {
    await monter()

    const section = await screen.findByRole('region', { name: 'Équipes non engagées' })
    expect(section).toHaveTextContent('Hennebont')
    expect(section).toHaveTextContent('Il manque des archers')
    expect(section).toHaveTextContent('Jean PETIT n’est pas en lice dans ce départ')
  })

  it('sans deux équipes engagées, dit qu’il n’y a rien à jouer et pourquoi', async () => {
    tableauCourant = { ...TABLEAU, effectif: 1, taille: 0, nb_tours: 0, duels: [] }
    await monter()

    expect(await screen.findByText(/Moins de deux équipes engagées/)).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Équipes non engagées' })).toHaveTextContent(
      'Hennebont',
    )
    expect(screen.getByText(/figurent ci-dessous/)).toBeInTheDocument()
  })

  it('le dit aussi quand aucune équipe n’est écartée', async () => {
    tableauCourant = {
      ...TABLEAU,
      effectif: 1,
      taille: 0,
      nb_tours: 0,
      duels: [],
      equipes_ecartees: [],
    }
    await monter()

    expect(await screen.findByText(/Moins de deux équipes engagées/)).toBeInTheDocument()
    expect(screen.queryByText(/figurent ci-dessous/)).toBeNull()
  })
})
