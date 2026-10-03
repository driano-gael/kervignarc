// Le réglage « par équipes » sur l'écran des phases (E13US004, CA 1). Monte `Phases` en entier :
// ce qu'on garde est « le réglage choisi part au serveur », pas « le contrôle sait s'afficher ».

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Categorie } from '../categories/api'
import type { ConfigPhase } from './api'
import { getCategories } from '../categories/api'
import { ajouterPhase, getPhases } from './api'
import { Phases } from './Phases'

vi.mock('./api', () => ({
  getPhases: vi.fn(),
  getAvancement: vi.fn(async () => []),
  ajouterPhase: vi.fn(),
  modifierPhase: vi.fn(),
  reordonnerPhases: vi.fn(),
  supprimerPhase: vi.fn(),
  changerStatutPhase: vi.fn(),
}))

vi.mock('../categories/api', () => ({ getCategories: vi.fn() }))

beforeEach(() => {
  vi.mocked(ajouterPhase).mockClear()
  vi.mocked(getCategories).mockResolvedValue([
    { id: 1, arme: 'Arc classique' } as Categorie,
    { id: 2, arme: 'Arc à poulies' } as Categorie,
  ])
})

function monter() {
  vi.mocked(getPhases).mockResolvedValue([])
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<Phases tournoiId={1} />, { wrapper: Enveloppe })
}

function configEnvoyee(): ConfigPhase {
  const appel = vi.mocked(ajouterPhase).mock.calls[0]
  if (appel === undefined) throw new Error('aucun POST de phase n’a été émis')
  return appel[1]
}

describe('le réglage « par équipes » d’une phase', () => {
  it('une élimination directe par équipes mixtes part au serveur comme telle', async () => {
    monter()
    await userEvent.selectOptions(await screen.findByLabelText(/Participants/), 'mixte')
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter la phase' }))

    await waitFor(() => expect(ajouterPhase).toHaveBeenCalled())
    expect(configEnvoyee().equipes).toBe('mixte')
  })

  it('par défaut, une phase reste individuelle', async () => {
    monter()
    await screen.findByLabelText(/Participants/)
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter la phase' }))

    await waitFor(() => expect(ajouterPhase).toHaveBeenCalled())
    expect(configEnvoyee().equipes).toBeNull()
  })

  it('retyper la phase hors élimination directe retire le réglage et l’efface', async () => {
    monter()
    await userEvent.selectOptions(await screen.findByLabelText(/Participants/), 'standard')
    await userEvent.selectOptions(screen.getByLabelText(/Type de la phase/), 'poules')

    expect(screen.queryByLabelText(/Participants/)).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter la phase' }))
    await waitFor(() => expect(ajouterPhase).toHaveBeenCalled())
    expect(configEnvoyee().equipes).toBeNull()
  })
})
