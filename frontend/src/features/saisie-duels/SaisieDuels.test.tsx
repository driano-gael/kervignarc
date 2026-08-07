// Test de **rendu** de l'écran de saisie en duels — et il existe pour une raison précise.
//
// La 2ᵉ revue d'E01US025 y a trouvé le bloquant le plus coûteux de l'US : l'écran alimentait son
// sélecteur de phase avec `GET /tournois/{id}/phases`, qui rend le **déroulé** (des `id` de
// `deroule_etape`), puis passait cet `id` à des routes qui résolvent une **`Phase`**. Deux tables,
// deux séquences d'`id` indépendantes. Le scoreur de l'après-midi écrasait donc les duels du matin,
// **sans la moindre erreur**.
//
// Rien ne pouvait le voir : `tsc` non (le type local `Phase {id, ordre, type}` est structurellement
// identique à une étape), `eslint` non, et aucun des tests de logique pure de cette feature
// (`duel.ts`, `etat.ts`, `rejeu.ts`) ne monte le composant — donc aucun ne sait **quel hook l'écran
// appelle**. C'est précisément l'angle mort que `PanneauBarrages.test.tsx` documente dans son propre
// en-tête, et qui vient de se reproduire ici. D'où ce fichier.
//
// On double **uniquement** les hooks de données ; le JSX est celui de production.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SaisieDuels } from './SaisieDuels'

const usePhases = vi.fn()
let departsRendus: { id: number; numero: number; horaire: string | null; etat: string }[] = []

vi.mock('../departs/api', () => ({
  getDeparts: () => Promise.resolve(departsRendus),
}))

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

// Le `QueryClient` et `useDeparts` sont ceux de **production** — seul l'appel HTTP est doublé. Un
// `useDeparts` doublé ne dirait rien du hook `useCreneauDesDuels`, qui est justement ce qu'on teste.
function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(<SaisieDuels tournoiId={1} />, { wrapper: Enveloppe })
}

describe('SaisieDuels — le créneau commande l’écran', () => {
  beforeEach(() => {
    usePhases.mockClear()
    departsRendus = [
      { id: 41, numero: 1, horaire: '09:00', etat: 'clos' },
      { id: 42, numero: 2, horaire: '14:00', etat: 'lance' },
    ]
  })

  it('demande les phases D’UN CRÉNEAU, jamais celles du tournoi', async () => {
    // ⚠️ Le bloquant. `usePhases` doit recevoir un `depart_id`, pas le `tournoiId` (1). Sans cette
    // assertion, remettre `usePhases(tournoiId)` laisse toute la suite verte.
    monter()
    await screen.findByRole('combobox', { name: /Phase de tableau à scorer/ })

    expect(usePhases).toHaveBeenCalledWith(41)
    expect(usePhases).not.toHaveBeenCalledWith(1)
  })

  it('ouvre sur le créneau DONT ON JOUE LES DUELS, pas sur celui qui tire sa qualif', async () => {
    // Le matin est `clos` (sa qualification est finie, donc ses duels se jouent) ; l'après-midi est
    // `lance` (il tire encore sa qualification). La règle de l'écran de salle rendrait
    // l'après-midi — qui n'a aucun duel à scorer.
    monter()
    await screen.findByRole('combobox', { name: /Phase de tableau à scorer/ })

    expect(usePhases).toHaveBeenCalledWith(41)
  })

  it('change de créneau à la demande, et REMET À ZÉRO le choix de phase', async () => {
    // Garder la phase de l'ancien créneau ferait scorer le tableau de l'autre départ sous un
    // identifiant parfaitement valide — donc sans erreur. C'est le même défaut d'un cran plus bas.
    monter()
    const phases = await screen.findByRole('combobox', { name: /Phase de tableau à scorer/ })
    await userEvent.selectOptions(phases, '901')
    expect((phases as HTMLSelectElement).value).toBe('901')

    await userEvent.selectOptions(screen.getByRole('combobox', { name: /Départ/ }), String(42))

    expect(usePhases).toHaveBeenCalledWith(42)
    const apres = screen.getByRole('combobox', { name: /Phase de tableau à scorer/ })
    expect((apres as HTMLSelectElement).value).toBe('')
  })

  it('ne lance aucune requête de phases tant que les créneaux ne sont pas arrivés', () => {
    // `enabled: departId !== null` — interroger `/departs/null/phases` produirait un 404 en boucle.
    monter()
    expect(usePhases).toHaveBeenCalledWith(null)
    expect(usePhases).not.toHaveBeenCalledWith(1)
  })

  it('le dit franchement quand le tournoi n’a aucun créneau', async () => {
    departsRendus = []
    monter()

    expect(await screen.findByText(/Aucun départ n’est encore défini/)).toBeInTheDocument()
  })
})
