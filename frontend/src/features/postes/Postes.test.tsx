// Planche A12 · postes en carte-tableau (E17US012) — CA : `stories/E17-fidelite-aux-maquettes.md`,
// puce « A12 » de l'arbitrage du 26/09/2026 : une ligne par poste de cible, son QR à la ligne.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PosteAdmin } from './api'
import { getPostes, getQrCible } from './api'
import { Postes } from './Postes'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getPostes: vi.fn(),
  getQrCible: vi.fn(),
}))

const POSTES: PosteAdmin[] = [
  { id: 7, tournoi_id: 1, cible_index: 1, code: '4K7-2M' },
  { id: 8, tournoi_id: 1, cible_index: 2, code: '9PX-4A' },
]

beforeEach(() => {
  vi.mocked(getPostes).mockResolvedValue(POSTES)
  vi.mocked(getQrCible).mockResolvedValue('data:image/svg+xml,%3Csvg%3E%3C%2Fsvg%3E')
})

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <Postes tournoiId={1} />
    </QueryClientProvider>,
  )
}

describe('Postes — carte-tableau de la planche A12', () => {
  it('un vrai <table> : poste, code, QR', async () => {
    monter()

    const table = await screen.findByRole('table')
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((th) => th.textContent),
    ).toEqual(['Poste', 'Code', 'QR'])
  })

  it('chaque ligne porte le QR de SA cible', async () => {
    monter()

    const ligne = (await screen.findByText('Cible 2')).closest('tr')
    expect(ligne).not.toBeNull()
    expect(within(ligne as HTMLElement).getByText('9PX-4A')).toBeInTheDocument()
    expect(
      await within(ligne as HTMLElement).findByAltText('QR de rattachement de la cible 2'),
    ).toBeInTheDocument()
  })
})
