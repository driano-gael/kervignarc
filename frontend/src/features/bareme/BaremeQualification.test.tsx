// Le preset « format club » du barème de qualification (E01US011, CA 5) — monté depuis l'écran,
// parce que le bouton porte sa propre constante, miroir de `domain/bareme.py`.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { getQualifications } from './api'
import { BaremeQualification } from './BaremeQualification'

vi.mock('./api', () => ({
  getBaremeDuTournoi: vi.fn(async () => null),
  definirBareme: vi.fn(),
  getQualifications: vi.fn(),
  definirBaremeEtape: vi.fn(),
}))

function monter() {
  vi.mocked(getQualifications).mockResolvedValue([
    {
      etape_id: 3,
      ordre: 1,
      libelle: 'Qualification',
      bareme: {
        nb_volees: 20,
        nb_fleches_par_volee: 3,
        nb_fleches_total: 60,
        score_max: 600,
        points_par_zone: {},
      },
      grain: null,
      grain_n_volees: null,
    },
  ])
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<BaremeQualification tournoiId={1} />, { wrapper: Enveloppe })
}

describe('le preset format club de la qualification', () => {
  it('pose 5 volées de 3 flèches, soit 150 points au plus', async () => {
    monter()
    await userEvent.click(await screen.findByRole('button', { name: 'Preset format club' }))

    expect(screen.getByRole('spinbutton', { name: 'Nombre de volées' })).toHaveValue(5)
    expect(screen.getByRole('spinbutton', { name: 'Nombre de flèches par volée' })).toHaveValue(3)
    expect(screen.getByText(/15 flèches · 150 points max/)).toBeInTheDocument()
  })

  it('le preset FFTA remet 20 volées de 3', async () => {
    monter()
    await userEvent.click(await screen.findByRole('button', { name: 'Preset format club' }))
    await userEvent.click(screen.getByRole('button', { name: 'Preset FFTA 18 m' }))

    expect(screen.getByRole('spinbutton', { name: 'Nombre de volées' })).toHaveValue(20)
  })
})
