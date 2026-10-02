// L'écran de la file du scoreur (E04US019), monté sur le vrai hook ; seul le réseau est doublé.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, renderHook, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { INTERVALLE_POLL_MS } from '../competition/hooks'
import type { Serie } from '../saisie/api'
import type { CibleEnAttente } from './api'
import { FileDuScoreur } from './FileDuScoreur'
import { useValiderSerie } from './hooks'

const getFileScoreur = vi.fn<(tournoiId: number, departId: number) => Promise<CibleEnAttente[]>>()
const validerSerie = vi.fn<(...args: unknown[]) => Promise<Serie>>()

vi.mock('./api', async (reel) => ({
  ...(await reel<typeof import('./api')>()),
  getFileScoreur: (tournoiId: number, departId: number) => getFileScoreur(tournoiId, departId),
  validerSerie: (...args: unknown[]) => validerSerie(...args),
}))

function enveloppe() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

function monter(onChoisir = vi.fn(), Enveloppe = enveloppe()) {
  render(<FileDuScoreur tournoiId={3} departId={7} onChoisir={onChoisir} />, {
    wrapper: Enveloppe,
  })
  return onChoisir
}

const CIBLE_14: CibleEnAttente = {
  cible_index: 14,
  attente_secondes: 60,
  archers: [{ archer_id: 5, nom: 'MARTIN', prenom: 'Sophie', position: 'A', attente_secondes: 60 }],
}

describe('FileDuScoreur', () => {
  beforeEach(() => {
    getFileScoreur.mockReset()
    validerSerie.mockReset()
  })
  afterEach(() => vi.useRealTimers())

  it("n'annonce aucun compte quand la file n'a pas pu être lue", async () => {
    getFileScoreur.mockRejectedValue(new Error('Réseau injoignable'))
    monter()

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByText(/en attente/)).not.toBeInTheDocument()
  })

  it('se met à jour sans geste du scoreur (CA « direct »)', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    getFileScoreur.mockResolvedValueOnce([]).mockResolvedValue([CIBLE_14])
    monter()
    expect(
      await screen.findByText('Rien à valider : les cibles tirent encore.'),
    ).toBeInTheDocument()

    await act(() => vi.advanceTimersByTimeAsync(INTERVALLE_POLL_MS))

    expect(await screen.findByText(/Cible 14/)).toBeInTheDocument()
  })

  it('une validation relit la file et transmet le créneau au serveur', async () => {
    getFileScoreur.mockResolvedValueOnce([CIBLE_14]).mockResolvedValue([])
    validerSerie.mockResolvedValue({ tournoi_id: 3, archer_id: 5, cumul: 54, volees: [] })
    const Enveloppe = enveloppe()
    monter(vi.fn(), Enveloppe)
    await screen.findByText(/Cible 14/)
    const { result } = renderHook(() => useValiderSerie(3), { wrapper: Enveloppe })

    await act(() => result.current.mutateAsync({ archerId: 5, departId: 7 }))

    expect(validerSerie).toHaveBeenCalledWith(3, 5, 7, expect.any(String))
    expect(
      await screen.findByText('Rien à valider : les cibles tirent encore.'),
    ).toBeInTheDocument()
  })

  it("garde l'ordre du serveur et affiche l'attente de chaque cible", async () => {
    getFileScoreur.mockResolvedValue([
      {
        cible_index: 14,
        attente_secondes: 260,
        archers: [
          { archer_id: 5, nom: 'MARTIN', prenom: 'Sophie', position: 'A', attente_secondes: 260 },
        ],
      },
      {
        cible_index: 12,
        attente_secondes: 35,
        archers: [
          { archer_id: 8, nom: 'DURAND', prenom: 'Jean', position: 'B', attente_secondes: 35 },
        ],
      },
    ])
    monter()

    const lignes = within(
      await screen.findByRole('list', { name: 'Cibles en attente de validation' }),
    ).getAllByRole('listitem')

    expect(getFileScoreur).toHaveBeenCalledWith(3, 7)
    expect(screen.getByText(/2 cibles en attente/)).toBeInTheDocument()
    expect(lignes[0]).toHaveTextContent('Cible 14 — attend depuis 4 min 20')
    expect(lignes[1]).toHaveTextContent('Cible 12 — attend depuis 35 s')
  })

  it('toucher un archer ouvre sa feuille', async () => {
    getFileScoreur.mockResolvedValue([
      {
        cible_index: 14,
        attente_secondes: 60,
        archers: [
          { archer_id: 5, nom: 'MARTIN', prenom: 'Sophie', position: 'A', attente_secondes: 60 },
        ],
      },
    ])
    const onChoisir = monter()

    await userEvent.click(
      await screen.findByRole('button', { name: 'Valider la feuille de MARTIN Sophie, cible 14' }),
    )

    expect(onChoisir).toHaveBeenCalledWith(5)
  })

  it('une file vide le dit, sans erreur', async () => {
    getFileScoreur.mockResolvedValue([])
    monter()

    expect(
      await screen.findByText('Rien à valider : les cibles tirent encore.'),
    ).toBeInTheDocument()
    expect(screen.getByText(/0 cible en attente/)).toBeInTheDocument()
  })
})
