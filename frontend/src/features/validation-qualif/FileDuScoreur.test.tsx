// L'écran de la file du scoreur (E04US019), monté sur le vrai hook ; seul le réseau est doublé.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CibleEnAttente } from './api'
import { FileDuScoreur } from './FileDuScoreur'

const getFileScoreur = vi.fn<(tournoiId: number, departId: number) => Promise<CibleEnAttente[]>>()

vi.mock('./api', async (reel) => ({
  ...(await reel<typeof import('./api')>()),
  getFileScoreur: (tournoiId: number, departId: number) => getFileScoreur(tournoiId, departId),
}))

function monter(onChoisir = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<FileDuScoreur tournoiId={3} departId={7} onChoisir={onChoisir} />, {
    wrapper: Enveloppe,
  })
  return onChoisir
}

describe('FileDuScoreur', () => {
  beforeEach(() => getFileScoreur.mockReset())

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
