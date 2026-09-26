// `usePlansDuTournoi` — l'adaptation entre le serveur et la règle `archersNonPlaces` (A09,
// E17US007). La règle pure est testée à part ; ici, ce que seul le hook décide : un 404
// `gabarit_du_tournoi_absent` veut dire « personne n'est placé », pas « donnée illisible ».

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import { getPlanDeCibles } from './api'
import { usePlansDuTournoi } from './hooks'

vi.mock('../departs/hooks', () => ({ useDeparts: () => ({ data: [{ id: 10 }] }) }))
vi.mock('./api', async (original) => ({
  ...(await original<typeof import('./api')>()),
  getPlanDeCibles: vi.fn(),
}))

function enveloppe() {
  const client = new QueryClient()
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

describe('usePlansDuTournoi', () => {
  it('salle pas encore définie : « sans gabarit », donc tous non placés', async () => {
    vi.mocked(getPlanDeCibles).mockRejectedValue(
      new ErreurApi(404, 'gabarit_du_tournoi_absent', 'Aucun gabarit.'),
    )
    const { result } = renderHook(() => usePlansDuTournoi(1), { wrapper: enveloppe() })

    await waitFor(() => expect(result.current).toBe('sans_gabarit'))
  })

  it('un plan pas encore lu : population inconnue', () => {
    vi.mocked(getPlanDeCibles).mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => usePlansDuTournoi(1), { wrapper: enveloppe() })

    expect(result.current).toBeNull()
  })

  it('tous les plans lus : on les rend', async () => {
    vi.mocked(getPlanDeCibles).mockResolvedValue({ depart_id: 10, cibles: [], conflits: [] })
    const { result } = renderHook(() => usePlansDuTournoi(1), { wrapper: enveloppe() })

    await waitFor(() =>
      expect(result.current).toEqual([{ depart_id: 10, cibles: [], conflits: [] }]),
    )
  })
})
