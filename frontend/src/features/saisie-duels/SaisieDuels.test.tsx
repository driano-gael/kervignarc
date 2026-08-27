// Test de **rendu** de l'écran de saisie en duels — et il existe pour une raison précise.
//
// La 2ᵉ revue d'E01US025 y a trouvé le bloquant le plus coûteux : l'écran alimentait son sélecteur
// avec `GET /tournois/{id}/phases`, qui rend le **déroulé**, puis passait cet `id` à des routes
// résolvant une **`Phase`** — deux séquences d'`id` indépendantes, donc le scoreur de l'après-midi
// écrasait les duels du matin **sans la moindre erreur**. Ni `tsc` ni les tests purs ne savent
// **quel hook l'écran appelle**. ⚠️ Le choix du créneau a déménagé dans `EspaceScoreur` (E05US030,
// `DETTE-056`) ; reste ici : **la phase demandée est celle du créneau reçu**.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SaisieDuels } from './SaisieDuels'

const usePhases = vi.fn()

vi.mock('./hooks', () => ({
  usePhases: (departId: number | null) => {
    usePhases(departId)
    return {
      data: departId === null ? undefined : (PHASES_PAR_DEPART[departId] ?? []),
      isError: false,
      isSuccess: departId !== null,
      error: null,
    }
  },
  useTableau: () => ({ isPending: true, isError: false, data: undefined, error: null }),
  useDuel: () => ({ isPending: true, isError: false, data: undefined, error: null }),
  useDuelsEnAttente: () => 0,
  useRejeuDuelsHorsLigne: () => undefined,
  useSaisirManche: () => MUTATION,
  useSaisirBarrage: () => MUTATION,
  useValiderDuel: () => MUTATION,
}))

const MUTATION = { mutate: vi.fn(), isPending: false, isError: false, error: null }

// ⚠️ Les identifiants de phase sont **volontairement éloignés** des identifiants de créneau et de
// tout ordinal : c'est ce qui rend le test capable de distinguer une phase d'une étape de déroulé.
// Avec des `id` 1 et 2 des deux côtés, l'ancien code aurait été vert.
const PHASES_PAR_DEPART: Record<number, { id: number; ordre: number; type: string }[]> = {
  41: [{ id: 901, ordre: 1, type: 'elimination_directe' }],
  42: [{ id: 902, ordre: 1, type: 'elimination_directe' }],
}

function monter(departId: number | null) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(<SaisieDuels tournoiId={1} departId={departId} />, { wrapper: Enveloppe })
}

describe('SaisieDuels — le créneau commande l’écran', () => {
  beforeEach(() => {
    usePhases.mockClear()
  })

  it('demande les phases D’UN CRÉNEAU, jamais celles du tournoi', async () => {
    // ⚠️ Le bloquant. `usePhases` doit recevoir le `depart_id` reçu en prop, pas le `tournoiId` (1).
    // Sans cette assertion, remettre `usePhases(tournoiId)` laisse toute la suite verte.
    monter(41)
    await screen.findByRole('combobox', { name: /Phase de tableau à scorer/ })

    expect(usePhases).toHaveBeenCalledWith(41)
    expect(usePhases).not.toHaveBeenCalledWith(1)
  })

  it('change de créneau à la demande, et REMET À ZÉRO le choix de phase', async () => {
    // Garder la phase de l'ancien créneau ferait scorer le tableau de l'autre départ sous un
    // identifiant parfaitement valide — donc sans erreur.
    const { rerender } = monter(41)
    const phases = await screen.findByRole('combobox', { name: /Phase de tableau à scorer/ })
    await userEvent.selectOptions(phases, '901')
    expect((phases as HTMLSelectElement).value).toBe('901')

    rerender(<SaisieDuels tournoiId={1} departId={42} />)

    expect(usePhases).toHaveBeenCalledWith(42)
    const apres = screen.getByRole('combobox', { name: /Phase de tableau à scorer/ })
    expect((apres as HTMLSelectElement).value).toBe('')
  })

  it('ne lance aucune requête de phases tant que les créneaux ne sont pas arrivés', () => {
    // `enabled: departId !== null` — interroger `/departs/null/phases` produirait un 404 en boucle.
    monter(null)
    expect(usePhases).toHaveBeenCalledWith(null)
    expect(usePhases).not.toHaveBeenCalledWith(1)
  })
})
