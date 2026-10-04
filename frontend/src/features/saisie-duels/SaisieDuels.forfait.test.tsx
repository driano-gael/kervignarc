// Test de **rendu** du câblage du forfait (E00US024) : `duellistesDuForfait` est testé seul dans
// `duel.test.ts`, mais rien ne prouvait que l'écran le lise — inverser la condition de rendu
// laissait toute la suite verte.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import type { FamilleDuel } from '../../shared/stores/fileDuelsHorsLigneStore'
import type { Duel } from './api'
import { DuelCharge } from './SaisieDuels'

const MUTATION = { mutate: vi.fn(), isPending: false, isError: false, error: null }

vi.mock('./hooks', () => ({
  useSaisirManche: () => MUTATION,
  useSaisirBarrage: () => MUTATION,
  useValiderDuel: () => MUTATION,
}))
vi.mock('../forfaits/hooks', () => ({
  useDeclarerForfaitDuel: () => MUTATION,
}))

const DUEL: Duel = {
  numero: 1,
  tour: 1,
  place_en_jeu: [1, 2],
  haut: { archer_id: 1, nom: 'DUPONT', prenom: 'Jean' },
  bas: { archer_id: 2, nom: 'MARTIN', prenom: 'Luc' },
  est_bye: false,
  mode: 'sets',
  nb_manches: 5,
  nb_fleches_par_volee: 3,
  points_pour_gagner: 6,
  nb_fleches_barrage: 1,
  zones: ['10', '9', 'M'],
  validee_par: null,
  manches: [],
  barrage: null,
  resultat: null,
}

function monter(duel: Duel, famille?: FamilleDuel) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(
    <DuelCharge
      tournoiId={1}
      phaseId={901}
      matchNumero={1}
      duel={duel}
      onValide={() => undefined}
      famille={famille}
    />,
    { wrapper: Enveloppe },
  )
}

const boutonsForfait = () => screen.queryAllByRole('button', { name: /abandonne$/ })

describe('DuelCharge — le bouton de forfait suit duellistesDuForfait', () => {
  it('le propose aux deux archers d’un duel de tableau (famille par défaut)', () => {
    monter(DUEL)
    expect(boutonsForfait().map((b) => b.textContent)).toEqual([
      'DUPONT Jean abandonne',
      'MARTIN Luc abandonne',
    ])
  })

  it('ne le propose pas en poule', () => {
    monter(DUEL, 'poule')
    expect(boutonsForfait()).toEqual([])
  })

  it('ne le propose pas sur un duel validé', () => {
    monter({ ...DUEL, validee_par: 'ROUX' })
    expect(boutonsForfait()).toEqual([])
  })

  it('ne le propose pas à un duel d’équipes', () => {
    monter({
      ...DUEL,
      haut: { archer_id: null, nom: 'Kervignac 1', prenom: '', equipe_id: 7, membres: [] },
      bas: { archer_id: null, nom: 'Lorient', prenom: '', equipe_id: 8, membres: [] },
    })
    expect(boutonsForfait()).toEqual([])
  })
})
