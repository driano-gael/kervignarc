// Une mutation de départ rafraîchit la grille horaire (E03US010) : l'heure d'un départ décale
// toute sa grille, et la grille vit dans un autre cache que la liste des départs.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { cleHoraires } from '../phases/hooks'
import { modifierDepart } from './api'
import { useModifierDepart } from './hooks'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  modifierDepart: vi.fn(async () => ({})),
}))

describe('useModifierDepart', () => {
  it('invalide la grille horaire du tournoi', async () => {
    const client = new QueryClient()
    client.setQueryData(cleHoraires(1), [])
    const enveloppe = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    )
    const { result } = renderHook(() => useModifierDepart(1), { wrapper: enveloppe })

    result.current.mutate({ departId: 3, entree: { horaire: '15:00', tarif_centimes: 800 } })

    await waitFor(() => expect(vi.mocked(modifierDepart)).toHaveBeenCalled())
    await waitFor(() => expect(client.getQueryState(cleHoraires(1))?.isInvalidated).toBe(true))
  })
})
