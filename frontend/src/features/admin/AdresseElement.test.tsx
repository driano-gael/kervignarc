// Garde-fou du 4ᵉ segment d'adresse (E16US010, ADR-0100) — **le test qui manquait**.
//
// ⚠️ Il monte `CoquilleAdmin`, pas une fonction pure. La réciprocité de `segmentsAdmin` était déjà
// prouvée dans `axes.test.ts`, et pourtant l'ouverture d'une fiche ne marchait pas : l'effet de
// canonisation d'adresse de la coquille rappelait `segmentsAdmin` **sans** son 4ᵉ argument et
// effaçait l'élément par `replaceState`. Un défaut de **câblage**, invisible à `tsc`, au lint et à
// toute fonction pure — exactement `DETTE-085` d'un cran plus haut. Ce fichier existe pour que la
// prochaine destination ajoutée ne le réintroduise pas.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Tournoi } from '../competition/api'
import { getTournois } from '../competition/api'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import { CoquilleAdmin } from './CoquilleAdmin'

vi.mock('../competition/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../competition/api')>()),
  getTournois: vi.fn(),
}))

// Tout ce que la sidebar et les écrans montés tirent par ailleurs : neutralisé pour n'observer
// que l'adresse. Ce test ne porte pas sur le contenu des écrans.
vi.mock('../recherche/api', () => ({
  chercher: vi.fn().mockResolvedValue({ resultats: [], total: 0 }),
}))
vi.mock('../jalons/api', () => ({ getApercusJalon: vi.fn().mockResolvedValue([]) }))
vi.mock('../archers/api', () => ({
  getArchers: vi.fn().mockResolvedValue([]),
  getDoublons: vi.fn().mockResolvedValue([]),
}))
vi.mock('../clubs/hooks', () => ({ useClubs: () => ({ data: [] }) }))
vi.mock('../categories/hooks', () => ({ useCategories: () => ({ data: [] }) }))
vi.mock('../blasons/hooks', () => ({ useBlasons: () => ({ data: [] }) }))

const TOURNOI: Tournoi = {
  id: 12,
  nom: 'Salle 18m',
  date: '2026-03-14',
  lieu: 'Kervignarc',
  type_tournoi: 'non_officiel',
  statut: 'brouillon',
}

function monter(enfants: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{enfants}</QueryClientProvider>)
}

beforeEach(() => {
  vi.mocked(getTournois).mockResolvedValue([TOURNOI])
  useSessionAdminStore.setState({ jeton: 'jeton-de-test' })
})

describe('le 4ᵉ segment d’adresse survit à la canonisation', () => {
  it('BLOQUANT corrigé — l’élément ouvert n’est PAS effacé de l’adresse', async () => {
    window.history.pushState(null, '', '/admin/12/gestion/inscriptions/57')

    monter(<CoquilleAdmin />)

    // La coquille corrige l'adresse au montage (destination validée contre l'axe). Elle doit
    // corriger la destination SANS perdre l'élément.
    await screen.findByText('Gestion')
    await waitFor(() => expect(window.location.pathname).toBe('/admin/12/gestion/inscriptions/57'))
  })

  it('une destination INVALIDE pour l’axe fait bien retomber l’adresse — et lâche l’élément', async () => {
    // Apparié au test ci-dessus : sans lui, un `chemAttendu` qui recopierait l'adresse telle quelle
    // rendrait le premier test vert sans rien canoniser. Ici `doublons` n'existe plus (E16US010),
    // donc on retombe sur l'ouverture de l'axe, et l'élément 57 n'a plus personne pour l'ouvrir.
    window.history.pushState(null, '', '/admin/12/gestion/doublons/57')

    monter(<CoquilleAdmin />)

    await waitFor(() => expect(window.location.pathname).toBe('/admin/12/gestion/inscriptions'))
  })
})
