// Test de **rendu** des marques de l'accueil admin (E00US024) : `marquesDeLAxe` est testé seul dans
// `axes.test.ts`, mais rien ne prouvait que les cartes d'axe le lisent — lui passer une liste vide,
// ou l'axe d'une autre carte, laissait toute la suite verte.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { TournoiEnListe } from '../competition/api'
import { getTournois } from '../competition/api'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import { CoquilleAdmin } from './CoquilleAdmin'

vi.mock('../competition/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../competition/api')>()),
  getTournois: vi.fn(),
}))
vi.mock('../recherche/api', () => ({
  chercher: vi.fn().mockResolvedValue({ resultats: [], total: 0 }),
}))
vi.mock('../jalons/api', () => ({ getApercusJalon: vi.fn().mockResolvedValue([]) }))

function tournoi(id: number, nom: string, statut: TournoiEnListe['statut']): TournoiEnListe {
  return {
    id,
    nom,
    date: '2026-03-14',
    lieu: 'Kervignarc',
    type_tournoi: 'non_officiel',
    statut,
    nb_inscrits: 0,
    nb_cibles: null,
  }
}

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <CoquilleAdmin />
    </QueryClientProvider>,
  )
}

// Témoin de chargement : la liste de l'accueil lit les mêmes tournois. Sans lui, les assertions
// d'**absence** passeraient avant l'arrivée des données — vertes par construction.
const donneesArrivees = (nom: string) => screen.findAllByText(nom)

const carte = async (libelle: string) =>
  (await screen.findByText(libelle, { selector: '.accueil-admin__titre' })).closest('button')!

beforeEach(() => {
  window.history.pushState(null, '', '/admin')
  useSessionAdminStore.setState({ jeton: 'jeton-de-test' })
})

describe('accueil admin — les cartes d’axe lisent marquesDeLAxe', () => {
  it('pilotage : compte et nomme les tournois lancés, pause comprise', async () => {
    vi.mocked(getTournois).mockResolvedValue([
      tournoi(1, 'Salle 18m', 'en_cours'),
      tournoi(2, 'Jeunes', 'en_pause'),
      tournoi(3, 'Coupe témoin', 'brouillon'),
    ])
    monter()
    const pilotage = await carte('Pilotage')
    expect(await within(pilotage).findByText('2 en cours')).toBeVisible()
    expect(within(pilotage).getByText('Salle 18m · Jeunes')).toBeVisible()
  })

  it('atelier seul porte « sans tournoi » ; gestion ne porte rien', async () => {
    vi.mocked(getTournois).mockResolvedValue([tournoi(1, 'Salle 18m', 'en_cours')])
    monter()
    await donneesArrivees('Salle 18m')
    expect(within(await carte('Atelier')).getByText('sans tournoi')).toBeVisible()
    const gestion = await carte('Gestion')
    expect(within(gestion).queryByText(/en cours|sans tournoi/)).toBeNull()
    expect(within(gestion).queryByText('Salle 18m')).toBeNull()
  })

  it('aucun tournoi lancé : jamais « 0 en cours »', async () => {
    vi.mocked(getTournois).mockResolvedValue([tournoi(3, 'Coupe témoin', 'brouillon')])
    monter()
    await donneesArrivees('Coupe témoin')
    const pilotage = await carte('Pilotage')
    expect(within(pilotage).queryByText(/en cours/)).toBeNull()
  })
})
