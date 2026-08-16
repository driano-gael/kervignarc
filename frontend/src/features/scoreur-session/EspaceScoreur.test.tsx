// Test de rendu de l'**espace scoreur** — il garde l'invariant qui a refermé `DETTE-056`
// (E05US030) : **un seul créneau pour tous les panneaux de saisie**.
//
// ⚠️ **Ces cas viennent de `SaisieDuels.test.tsx`**, où ils vivaient tant que chaque panneau
// choisissait son créneau pour son compte. Le défaut qu'ils gardent n'a pas changé de nature en
// changeant de domicile : quatre sélecteurs indépendants faisaient scorer les rencontres du mauvais
// départ **avec des identifiants valides, donc sans la moindre erreur**. Ce qui se vérifie ici est
// donc « il n'y en a qu'un, et les quatre panneaux reçoivent la même valeur » — précisément ce
// qu'aucun test de panneau ne peut voir tout seul.
//
// Les quatre panneaux sont doublés par une étiquette qui **affiche le créneau reçu** : c'est la
// seule façon d'observer qu'ils partagent bien la même source.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EspaceScoreur } from './EspaceScoreur'

let departsRendus: { id: number; numero: number; horaire: string | null; etat: string }[] = []

vi.mock('../departs/api', () => ({
  getDeparts: () => Promise.resolve(departsRendus),
}))

vi.mock('../../shared/stores/sessionScoreurStore', () => ({
  useSessionScoreurStore: (selecteur: (etat: unknown) => unknown) =>
    selecteur({ scoreur: { nom: 'Camille', tournoi_id: 1 }, jeton: 'x' }),
}))

vi.mock('./hooks', () => ({
  useConnexionScoreur: () => MUTATION,
  useDeconnexionScoreur: () => MUTATION,
}))

const MUTATION = { mutate: vi.fn(), isPending: false, isError: false, error: null }

// Chaque panneau doublé annonce le créneau qu'il a reçu. Un panneau qui en recevrait un autre — ou
// qui irait le chercher lui-même — se verrait immédiatement.
function panneau(nom: string) {
  return ({ departId }: { departId: number | null }) => (
    <p>
      {nom} : {String(departId)}
    </p>
  )
}

vi.mock('../saisie-duels/SaisieDuels', () => ({ SaisieDuels: panneau('duels') }))
vi.mock('../poules/SaisiePoules', () => ({ SaisiePoules: panneau('poules') }))
vi.mock('../big-shoot-off/SaisieBigShootOff', () => ({ SaisieBigShootOff: panneau('bso') }))
vi.mock('../suisse/SaisieSuisse', () => ({ SaisieSuisse: panneau('suisse') }))
vi.mock('../forfaits/PanneauForfaitsQualif', () => ({ PanneauForfaitsQualif: () => null }))

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(<EspaceScoreur />, { wrapper: Enveloppe })
}

describe('EspaceScoreur — un seul créneau pour tous les panneaux', () => {
  beforeEach(() => {
    departsRendus = [
      { id: 41, numero: 1, horaire: '09:00', etat: 'clos' },
      { id: 42, numero: 2, horaire: '14:00', etat: 'lance' },
    ]
  })

  it('n’affiche qu’UN sélecteur de créneau', async () => {
    // Le cœur de `DETTE-056` : il y en avait un par panneau.
    monter()
    await screen.findByText('duels : 41')

    expect(screen.getAllByRole('combobox', { name: /Départ/ })).toHaveLength(1)
  })

  it('ouvre sur le créneau DONT ON JOUE LES DUELS, pas sur celui qui tire sa qualif', async () => {
    // Le matin est `clos` (sa qualification est finie, donc ses duels se jouent) ; l'après-midi est
    // `lance` (il tire encore sa qualification). La règle de l'écran de salle rendrait
    // l'après-midi — qui n'a aucun duel à scorer.
    monter()

    expect(await screen.findByText('duels : 41')).toBeInTheDocument()
  })

  it('donne le MÊME créneau aux quatre panneaux, et le changement les suit tous', async () => {
    monter()
    await screen.findByText('duels : 41')
    for (const nom of ['poules', 'bso', 'suisse']) {
      expect(screen.getByText(`${nom} : 41`)).toBeInTheDocument()
    }

    await userEvent.selectOptions(screen.getByRole('combobox', { name: /Départ/ }), '42')

    for (const nom of ['duels', 'poules', 'bso', 'suisse']) {
      expect(screen.getByText(`${nom} : 42`)).toBeInTheDocument()
    }
  })

  it('le dit franchement quand le tournoi n’a aucun créneau', async () => {
    departsRendus = []
    monter()

    expect(await screen.findByText(/Aucun départ n’est encore défini/)).toBeInTheDocument()
  })
})
