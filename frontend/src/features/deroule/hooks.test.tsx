// Test de **couture** : enregistrer un brouillon doit périmer le diagnostic (E01US024).
//
// C'est le seul test de hook de cette feature, et il est là pour une raison précise : le défaut
// qu'il fixe est passé au travers de tout le reste. Les clés `['patrimoine','formats']` et
// `['deroule','diagnostic']` n'ont aucun recouvrement de préfixe, donc enregistrer n'invalidait
// rien ; avec `staleTime: 30_000`, `refetchOnWindowFocus: false` et un composant qui ne remonte
// pas, le schéma restait figé sur la version d'avant — pendant que l'écran retirait l'avertissement
// « modifications non enregistrées ». Ni `tsc`, ni `eslint`, ni un test de logique pure ne pouvaient
// le voir : la faute est **entre** deux hooks, pas dans l'un d'eux.
//
// La convention « le JSX ne se teste pas » ne couvre pas un hook : `shared/navigation/useChemin` a
// le sien, et `@testing-library/react` est déjà en devDependencies. On ne double que les **appels
// HTTP** (`./api`, `../patrimoine/api`) : les hooks eux-mêmes, et le vrai `QueryClient`, sont ceux
// de production — sans quoi le test ne dirait rien de la couture qu'il prétend vérifier.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { modifierFormat } from '../patrimoine/api'
import { getDiagnostic, type Diagnostic } from './api'
import { useDiagnostic, useEnregistrerBrouillon } from './hooks'

vi.mock('./api', () => ({ getDiagnostic: vi.fn(), simulerFormat: vi.fn(), EFFECTIF_MAX: 200 }))
vi.mock('../patrimoine/api', () => ({ modifierFormat: vi.fn() }))

const DIAGNOSTIC: Diagnostic = {
  effectif: 120,
  applicable: true,
  blocs: [],
  anomalies: [],
  effectif_minimum: 1,
}

function enveloppe(client: QueryClient) {
  return function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

// `staleTime` reproduit celui de `app/queryClient.ts` : sans invalidation explicite, la query n'est
// **ni** périmée **ni** refetchée — c'est précisément ce qui masquait le défaut.
function clientDeTest() {
  return new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: false } } })
}

describe('useEnregistrerBrouillon', () => {
  beforeEach(() => {
    vi.mocked(getDiagnostic).mockResolvedValue(DIAGNOSTIC)
    vi.mocked(modifierFormat).mockResolvedValue({
      id: 1,
      nom: 'X',
      origine: 'utilisateur',
      etapes: [],
      effectif_minimum_exige: null,
    })
  })

  it('périme le diagnostic après un enregistrement — sinon le schéma reste figé', async () => {
    const rendu = renderHook(
      () => ({ diagnostic: useDiagnostic(1, 120), sauvegarde: useEnregistrerBrouillon() }),
      { wrapper: enveloppe(clientDeTest()) },
    )
    await waitFor(() => expect(rendu.result.current.diagnostic.data).toEqual(DIAGNOSTIC))
    expect(getDiagnostic).toHaveBeenCalledTimes(1)

    await act(async () => {
      rendu.result.current.sauvegarde.enregistrer({ id: 1, entree: { nom: 'X', etapes: [] } })
    })

    await waitFor(() => expect(getDiagnostic).toHaveBeenCalledTimes(2))
  })

  it('relaie le `onSuccess` de l’appelant — c’est lui qui retire « non enregistré »', async () => {
    const rendu = renderHook(() => useEnregistrerBrouillon(), {
      wrapper: enveloppe(clientDeTest()),
    })
    const apresSucces = vi.fn()

    await act(async () => {
      rendu.result.current.enregistrer(
        { id: 1, entree: { nom: 'X', etapes: [] } },
        { onSuccess: apresSucces },
      )
    })

    await waitFor(() => expect(apresSucces).toHaveBeenCalledTimes(1))
  })

  it('n’expose pas `mutate` — l’invalidation ne doit pas pouvoir être court-circuitée', () => {
    const rendu = renderHook(() => useEnregistrerBrouillon(), {
      wrapper: enveloppe(clientDeTest()),
    })

    expect(rendu.result.current).not.toHaveProperty('mutate')
    expect(rendu.result.current).not.toHaveProperty('mutateAsync')
  })
})
