// Test de rendu du **signalement de doublon sur la ligne d'archer** (E16US010).
//
// CA : « une simple icône cliquable sur la ligne de l'archer peut suffire », qui « montre le
// problème et propose l'action, au lieu d'un écran dédié qui pollue ». ⚠️ **Monter l'écran, pas
// le composant** : un test qui monterait `FusionDoublon` seule resterait vert après l'avoir
// détachée de la liste — le défaut exact de `DETTE-085`, que `tsc` ne voit pas.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Archer, Doublon } from './api'
import { getArchers, getDoublons } from './api'
import { Archers } from './Archers'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getArchers: vi.fn(),
  getDoublons: vi.fn(),
}))

// Décor de la ligne : ni club, ni catégorie, ni blason n'entrent dans ce que le test observe.
vi.mock('../clubs/hooks', () => ({ useClubs: () => ({ data: [] }) }))
vi.mock('../categories/hooks', () => ({ useCategories: () => ({ data: [] }) }))
vi.mock('../blasons/hooks', () => ({ useBlasons: () => ({ data: [] }) }))

function archer(id: number, prenom: string): Archer {
  return {
    id,
    tournoi_id: 1,
    nom: 'Dupont',
    prenom,
    categorie_id: 1,
    cible: null,
    club_id: null,
    handicap_officiel: null,
    handicap_surcharge: null,
    handicap: 0,
  }
}

const JEAN = archer(1, 'Jean')
const JHEAN = archer(2, 'Jhean')
const LUC = archer(3, 'Luc')

function monter(enfants: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{enfants}</QueryClientProvider>)
}

beforeEach(() => {
  vi.mocked(getArchers).mockResolvedValue([JEAN, JHEAN, LUC])
  vi.mocked(getDoublons).mockReset()
  vi.mocked(getDoublons).mockResolvedValue([])
})

const PAIRE: Doublon = { niveau: 'probable', a: JEAN, b: JHEAN }

describe('signalement de doublon sur la ligne', () => {
  it('CA — la fiche rapprochée porte un signalement cliquable, qui NOMME le niveau', async () => {
    // Du texte et non une icône seule : « probable » ne se devine pas d'un pictogramme, et un
    // signal qui n'existe qu'en image ne se lit pas au lecteur d'écran.
    vi.mocked(getDoublons).mockResolvedValue([PAIRE])

    monter(<Archers tournoiId={1} />)

    expect(await screen.findAllByRole('button', { name: 'Doublon probable' })).toHaveLength(2)
  })

  it('CA — l’archer que rien ne rapproche n’est PAS signalé', async () => {
    // Négatif apparié au positif ci-dessus : un signalement sur toutes les lignes ne dirait rien.
    vi.mocked(getDoublons).mockResolvedValue([PAIRE])

    monter(<Archers tournoiId={1} />)

    await screen.findAllByRole('button', { name: 'Doublon probable' })
    const ligneDeLuc = screen.getByText(/Luc/).closest('li')
    expect(ligneDeLuc).not.toBeNull()
    expect(ligneDeLuc?.textContent).not.toContain('Doublon')
  })

  it('CA — cliquer déplie l’ACTION sur place : c’est ce qui remplace l’écran dédié', async () => {
    vi.mocked(getDoublons).mockResolvedValue([PAIRE])

    monter(<Archers tournoiId={1} />)

    const marques = await screen.findAllByRole('button', { name: 'Doublon probable' })
    expect(screen.queryByRole('button', { name: 'Garder cette fiche' })).not.toBeInTheDocument()
    await userEvent.click(marques[0] as HTMLElement)

    expect(await screen.findAllByRole('button', { name: 'Garder cette fiche' })).toHaveLength(2)
  })

  it('la vue d’ensemble que l’écran portait tient en une phrase chiffrée', async () => {
    // Sans elle, on ne saurait qu'il y a des doublons qu'en tombant dessus ligne par ligne — la
    // perte réelle du retrait de l'écran dédié.
    vi.mocked(getDoublons).mockResolvedValue([PAIRE])

    monter(<Archers tournoiId={1} />)

    expect(await screen.findByText(/1 rapprochement de fiches/)).toBeInTheDocument()
  })

  it('aucun doublon : aucune phrase, aucun signalement', async () => {
    monter(<Archers tournoiId={1} />)

    await screen.findByText(/Luc/)
    expect(screen.queryByText(/rapprochement/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Doublon/ })).not.toBeInTheDocument()
  })
})
