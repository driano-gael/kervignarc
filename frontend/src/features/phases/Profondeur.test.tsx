// Le réglage « jusqu'où classer » sur les phases d'un **tournoi réel** (E06US006, ADR-0070).
//
// Ce fichier n'existait pas, et c'est ce que la revue a relevé : le CA exige le réglage « depuis
// « Composer un format » **et** depuis les phases d'un tournoi », mais seul le premier écran était
// testé — alors que celui-ci est le seul des deux à écrire dans une base.
//
// Il porte en outre le piège que l'ADR qualifie de plus coûteux : l'édition d'une phase est un
// `PUT` **total**, donc un champ non réémis est **effacé**. Une profondeur effacée fait rejouer un
// tournoi tronqué au podium — c'est l'histoire déjà vécue avec `barrage_jusqu_au`, documentée dans
// `api.ts`, et que rien ne figeait.
//
// On double les **appels HTTP** seulement : les hooks et le `QueryClient` sont ceux de production,
// sans quoi le test ne dirait rien de ce qu'il prétend vérifier (même parti que `deroule/hooks`).

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { modifierPhase, type ConfigPhase, type EtapeDeroule } from './api'
import { FormulairePhase } from './Phases'

vi.mock('./api', () => ({
  getPhases: vi.fn(),
  getAvancement: vi.fn(),
  ajouterPhase: vi.fn(),
  modifierPhase: vi.fn(),
  reordonnerPhases: vi.fn(),
  supprimerPhase: vi.fn(),
  changerStatutPhase: vi.fn(),
}))

// Une **étape du déroulé** : cet écran ne compose plus que la définition (ADR-0076). Elle n'a donc
// ni `statut` ni `depart_id` — c'est précisément ce que la séparation garantit.
const PHASE: EtapeDeroule = {
  id: 7,
  tournoi_id: 1,
  ordre: 2,
  type: 'elimination_directe',
  sources: [],
  effectif: 16,
  barrage_jusqu_au: null,
  profondeur: { nom: 'un_vers_n', jusqu_au: null },
  poules: null,
  big_shoot_off: null,
  suisse: null,
  colline: null,
  decoupage: null,
  titre: null,
  nb_volees: null,
  // E05US033 : les deux réglages neufs. `null` / `[]` = le comportement d'avant l'US.
  arrets: [],
}

function poser(phase: EtapeDeroule = PHASE) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<FormulairePhase tournoiId={1} phases={[phase]} phase={phase} />, { wrapper: Enveloppe })
}

const configEnvoyee = (): ConfigPhase =>
  (vi.mocked(modifierPhase).mock.calls[0] as [number, number, ConfigPhase])[2]

describe('profondeur sur les phases d’un tournoi', () => {
  it('réémet la profondeur quand on ne corrige que l’effectif', async () => {
    vi.mocked(modifierPhase).mockResolvedValue(PHASE)
    poser()

    const effectif = screen.getByLabelText(/Effectif/)
    await userEvent.clear(effectif)
    await userEvent.type(effectif, '8')
    await userEvent.click(screen.getByRole('button', { name: /Enregistrer|Valider/ }))

    await waitFor(() => expect(modifierPhase).toHaveBeenCalled())
    // Le point important du scénario 2 de la fiche fonctionnelle : corriger un détail ne doit pas
    // effacer en silence le réglage qui change tout le tournoi.
    expect(configEnvoyee().profondeur).toEqual({ nom: 'un_vers_n', jusqu_au: null })
  })

  it('affiche le réglage que porte la phase', () => {
    poser()

    expect(screen.getByLabelText(/classer/)).toHaveProperty('value', 'integral')
  })

  it('n’offre pas le réglage sur un type sans tableau', async () => {
    poser()

    await userEvent.selectOptions(screen.getByLabelText(/Type de la phase/), 'poules')

    expect(screen.queryByLabelText(/classer/)).toBeNull()
  })
})
