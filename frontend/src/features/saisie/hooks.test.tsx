// Test de **couture** sur `useSaisirVolee` : un refus de préséance doit relire la vérité serveur.
//
// ⚠️ Il n'existait pas en 1ʳᵉ passe d'E16US020, et deux axes de revue ont trouvé le même trou :
// `Saisie.test.tsx` mocke **tout** `./hooks`, donc le `onError` livré par l'US n'était exercé par
// rien — alors que le message rendu à l'écran affirme « Le score affiché est celui qui fait foi »,
// ce qui n'est vrai que grâce à cette invalidation. On ne double que l'appel HTTP.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { ErreurApi } from '../../shared/api/client'
import { saisirVolee } from './api'
import { cleSerie, useSaisirVolee } from './hooks'

vi.mock('./api', () => ({ saisirVolee: vi.fn() }))

const CORPS = {
  tournoi_id: 1,
  archer_id: 7,
  numero: 1,
  valeurs: ['10', '9', '9'],
  saisie_par: 'DURAND',
  identifiant_saisie: 'id-1',
}

function monter(client: QueryClient) {
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return renderHook(() => useSaisirVolee(1, 7), { wrapper: Enveloppe })
}

describe('useSaisirVolee — refus de préséance (E16US020)', () => {
  it('relit la série pour que la tablette n’affiche pas le score qu’elle vient de taper', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const invalider = vi.spyOn(client, 'invalidateQueries')
    vi.mocked(saisirVolee).mockRejectedValue(
      new ErreurApi(409, 'ecriture_de_role_inferieur', 'Saisie par l’organisateur.'),
    )

    const { result } = monter(client)
    result.current.mutate(CORPS)

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(invalider).toHaveBeenCalledWith({ queryKey: cleSerie(1, 7) })
  })

  it('ne relit RIEN sur un refus qui n’a rien changé en base', async () => {
    // ⚠️ Sans ce jumeau, invalider sur toute erreur passerait inaperçu : une panne réseau
    // relancerait une lecture qui échouera à son tour, et l'écran retomberait en erreur pour rien.
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const invalider = vi.spyOn(client, 'invalidateQueries')
    vi.mocked(saisirVolee).mockRejectedValue(
      new ErreurApi(403, 'saisie_hors_cible', 'Archer hors de votre cible.'),
    )

    const { result } = monter(client)
    result.current.mutate(CORPS)

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(invalider).not.toHaveBeenCalled()
  })
})
