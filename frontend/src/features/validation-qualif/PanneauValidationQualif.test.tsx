// Le créneau voyage de l'écran au serveur (E04US019, CA « geste ») — panneau monté, réseau doublé.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Depart } from '../departs/api'
import type { Serie } from '../saisie/api'
import type { CibleEnAttente } from './api'
import { PanneauValidationQualif } from './PanneauValidationQualif'

const getDeparts = vi.fn<(tournoiId: number) => Promise<Depart[]>>()
const getFileScoreur = vi.fn<(tournoiId: number, departId: number) => Promise<CibleEnAttente[]>>()
const getSerieScoreur =
  vi.fn<(tournoiId: number, archerId: number, departId: number | null) => Promise<Serie>>()
const validerSerie = vi.fn<(...args: unknown[]) => Promise<Serie>>()

vi.mock('../departs/api', async (reel) => ({
  ...(await reel<typeof import('../departs/api')>()),
  getDeparts: (tournoiId: number) => getDeparts(tournoiId),
}))
vi.mock('../competition/hooks', async (reel) => ({
  ...(await reel<typeof import('../competition/hooks')>()),
  useClassement: () => ({ data: undefined, isPending: false, isError: false, error: null }),
}))
vi.mock('./api', async (reel) => ({
  ...(await reel<typeof import('./api')>()),
  getFileScoreur: (tournoiId: number, departId: number) => getFileScoreur(tournoiId, departId),
  getSerieScoreur: (tournoiId: number, archerId: number, departId: number | null) =>
    getSerieScoreur(tournoiId, archerId, departId),
  validerSerie: (...args: unknown[]) => validerSerie(...args),
}))

function depart(id: number, numero: number, etat: Depart['etat']): Depart {
  return {
    id,
    tournoi_id: 3,
    numero,
    horaire: numero === 1 ? '09:00' : '14:00',
    tarif_centimes: 0,
    quota: null,
    etat,
    effectif: 1,
  }
}

const FILE: CibleEnAttente[] = [
  {
    cible_index: 4,
    attente_secondes: 90,
    archers: [
      { archer_id: 5, nom: 'MARTIN', prenom: 'Sophie', position: 'A', attente_secondes: 90 },
    ],
  },
]

const FEUILLE: Serie = {
  tournoi_id: 3,
  archer_id: 5,
  cumul: 0,
  volees: [1, 2].map((numero) => ({
    numero,
    valeurs: ['10', '9', '8'],
    saisie_par: null,
    validee_par: null,
    verrouillee: false,
    en_correction: false,
    correction_ouverte_par: null,
    lot_validation: null,
    saisie_le: null,
  })),
}

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<PanneauValidationQualif tournoiId={3} />, { wrapper: Enveloppe })
  return client
}

const boutonArcher = () =>
  screen.findByRole('button', { name: 'Valider la feuille de MARTIN Sophie, cible 4' })

describe('PanneauValidationQualif — le créneau voyage', () => {
  beforeEach(() => {
    for (const double of [getDeparts, getFileScoreur, getSerieScoreur, validerSerie]) {
      double.mockReset()
    }
    getFileScoreur.mockResolvedValue(FILE)
    getSerieScoreur.mockResolvedValue(FEUILLE)
    validerSerie.mockResolvedValue(FEUILLE)
  })

  it('le créneau choisi part avec la lecture de la feuille et la validation', async () => {
    getDeparts.mockResolvedValue([depart(7, 1, 'lance'), depart(8, 2, 'ouvert')])
    monter()

    await userEvent.selectOptions(await screen.findByLabelText(/Départ à valider/), '8')
    await userEvent.click(await boutonArcher())
    await userEvent.click(await screen.findByRole('button', { name: 'Valider' }))

    expect(getFileScoreur).toHaveBeenLastCalledWith(3, 8)
    expect(getSerieScoreur).toHaveBeenCalledWith(3, 5, 8)
    await waitFor(() => expect(validerSerie).toHaveBeenCalledWith(3, 5, 8, expect.any(String)))
  })

  it('une bascule implicite du créneau ferme la feuille au lieu de la relire ailleurs', async () => {
    getDeparts.mockResolvedValue([depart(7, 1, 'lance'), depart(8, 2, 'ouvert')])
    const client = monter()
    await userEvent.click(await boutonArcher())
    expect(await screen.findByText(/Total validé/)).toBeInTheDocument()

    // Le matin se clôt, l'après-midi est lancé : `departDeSalle` bascule sans geste du scoreur.
    getDeparts.mockResolvedValue([depart(7, 1, 'clos'), depart(8, 2, 'lance')])
    await client.invalidateQueries()

    await waitFor(() => expect(screen.queryByText(/Total validé/)).not.toBeInTheDocument())
    expect(getSerieScoreur).not.toHaveBeenCalledWith(3, 5, 8)
  })
})
