// Tests de rendu de la **fiche d'archer du pilotage** (E16US010).
//
// CA : « ouvrir sa fiche en consultation avec ses informations du tournoi, puis possibilité d'agir
// dessus si besoin ». Ce qui se vérifie ici est ce qu'aucun type ne prouve : que la destination
// vide dit **par où on y entre**, qu'un archer d'une autre édition est nommé comme tel plutôt que
// rendu par un écran blanc, et que les deux actions sont réellement câblées.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Archer } from './api'
import { declarerForfaitQualif } from '../forfaits/api'
import { getArchers } from './api'
import { FicheArcherPilotage } from './FicheArcherPilotage'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getArchers: vi.fn(),
}))

vi.mock('../clubs/hooks', () => ({ useClubs: () => ({ data: [{ id: 5, nom: 'Arc Club' }] }) }))
vi.mock('../categories/hooks', () => ({
  useCategories: () => ({ data: [{ id: 1, libelle: 'Senior 1 H', blason_id: null }] }),
}))
vi.mock('../blasons/hooks', () => ({ useBlasons: () => ({ data: [] }) }))
vi.mock('../forfaits/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../forfaits/api')>()),
  declarerForfaitQualif: vi.fn(),
}))
// La place tire départs et plans : neutralisée pour n'observer que la fiche.
vi.mock('../placement/PlaceDeLArcher', () => ({ PlaceDeLArcher: () => null }))

const JEAN: Archer = {
  id: 57,
  tournoi_id: 12,
  nom: 'Lévêque',
  prenom: 'Jean',
  categorie_id: 1,
  cible: null,
  club_id: 5,
  handicap_officiel: null,
  handicap_surcharge: null,
  handicap: 0,
}

function monter(enfants: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{enfants}</QueryClientProvider>)
}

function fiche(
  archerId: number | null,
  actions: Partial<{ corriger: () => void; placer: () => void }> = {},
) {
  return (
    <FicheArcherPilotage
      tournoiId={12}
      archerId={archerId}
      onCorrigerLaFiche={actions.corriger ?? vi.fn()}
      onModifierLePlacement={actions.placer ?? vi.fn()}
    />
  )
}

beforeEach(() => {
  vi.mocked(getArchers).mockResolvedValue([JEAN])
})

describe('fiche d’archer du pilotage', () => {
  it('sans archer, la destination dit PAR OÙ on y entre', async () => {
    // Une destination qui s'ouvre vide et muette se lit comme un écran cassé.
    monter(fiche(null))

    expect(await screen.findByText(/Cherchez un archer dans la barre de recherche/)).toBeVisible()
  })

  it('CA — la fiche rend les informations du tournoi, en consultation', async () => {
    monter(fiche(57))

    expect(await screen.findByText('Lévêque Jean')).toBeVisible()
    expect(screen.getByText(/Senior 1 H · Arc Club/)).toBeVisible()
  })

  it('un archer d’une autre édition est NOMMÉ, pas rendu par un écran blanc', async () => {
    // Le lien existe (la recherche traverse les éditions) ; l'écran doit expliquer, pas se taire.
    monter(fiche(999))

    expect(await screen.findByText(/n’est pas inscrit à ce tournoi/)).toBeVisible()
  })

  it('CA — les deux actions sont câblées', async () => {
    const corriger = vi.fn()
    const placer = vi.fn()
    monter(fiche(57, { corriger, placer }))

    await userEvent.click(await screen.findByRole('button', { name: 'Corriger sa fiche' }))
    await userEvent.click(screen.getByRole('button', { name: 'Modifier son placement' }))

    expect(corriger).toHaveBeenCalledWith(57)
    expect(placer).toHaveBeenCalled()
  })

  it('déclare un forfait de qualification en portée ADMIN', async () => {
    // ⚠️ Ce test **remplace** son inverse, qui vérifiait l'absence de bouton ET nommait sa cause
    // (« depuis l'espace scoreur ») précisément pour rougir le jour de l'élargissement. Il a
    // rougi : arbitrage du commanditaire du 30/08/2026, la route de qualification s'ouvre à
    // l'organisateur. ⚠️ **La portée `'admin'` est le cœur de l'assertion** : un appel parti en
    // `'scoreur'` depuis l'admin joindrait un jeton absent et repartirait en 401, sans que le
    // rendu change d'un pixel.
    vi.mocked(declarerForfaitQualif).mockResolvedValue({
      id: 1,
      tournoi_id: 12,
      archer_id: 57,
      phase_id: 3,
      nature: 'abandon',
      declare_par: 'Administrateur',
      declare_le: '2026-08-30T16:00:00+00:00',
      motif: null,
    })
    monter(fiche(57))

    await screen.findByText('Lévêque Jean')
    await userEvent.click(screen.getByRole('button', { name: 'Déclarer un forfait' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmer le forfait' }))

    expect(declarerForfaitQualif).toHaveBeenCalledWith(12, 57, 'abandon', undefined, 'admin')
    expect(await screen.findByText(/Forfait enregistré/)).toBeVisible()
  })

  it('renvoie l’annulation là où elle se fait, sans armer de bouton qui ne saurait rien annuler', async () => {
    // `D-15` reste tenu par le panneau scoreur : la fiche ne sait pas *qui* est déjà forfait.
    vi.mocked(declarerForfaitQualif).mockResolvedValue({
      id: 1,
      tournoi_id: 12,
      archer_id: 57,
      phase_id: 3,
      nature: 'abandon',
      declare_par: 'Administrateur',
      declare_le: '2026-08-30T16:00:00+00:00',
      motif: null,
    })
    monter(fiche(57))

    await screen.findByText('Lévêque Jean')
    await userEvent.click(screen.getByRole('button', { name: 'Déclarer un forfait' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmer le forfait' }))

    expect(await screen.findByText(/l’espace scoreur/)).toBeVisible()
  })
})
