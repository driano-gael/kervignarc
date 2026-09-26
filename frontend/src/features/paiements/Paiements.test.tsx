// L'écran des paiements monté en entier, planche A17 (E17US012) — tests écrits depuis le CA :
// `stories/E17-fidelite-aux-maquettes.md`, E17US012, puce « A17 » et son arbitrage du 26/09/2026.
// Les règles elles-mêmes sont couvertes par `planche.test.ts` ; ici, le **câblage** jusqu'à l'écran.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Completude } from '../completude/api'
import { getCompletude } from '../completude/api'
import type { LignePaiementArcher } from './api'
import { getPaiementsArchers, getPaiementsClubs, getRemboursements } from './api'
import { Paiements } from './Paiements'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getPaiementsArchers: vi.fn(),
  getPaiementsClubs: vi.fn(),
  getRemboursements: vi.fn(),
}))

vi.mock('../completude/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../completude/api')>()),
  getCompletude: vi.fn(),
}))

const COMPLETUDE: Completude = { sportif: [], hors_sportif: [], sportif_complet: false }

const MARTIN: LignePaiementArcher = {
  archer_id: 1,
  nom: 'MARTIN',
  prenom: 'Sophie',
  club_id: 4,
  recap: { du_centimes: 1400, paye_centimes: 0, reste_centimes: 1400 },
  club: 'Kervignac',
  categorie: 'Senior 1 Femme',
  // Midi UTC : le même jour de calendrier dans tous les fuseaux d'Europe.
  dette: { depuis: '2026-11-02T12:00:00Z' },
  nb_inscriptions: 1,
}

const DURAND: LignePaiementArcher = {
  archer_id: 2,
  nom: 'DURAND',
  prenom: 'Paul',
  club_id: null,
  recap: { du_centimes: 1000, paye_centimes: 0, reste_centimes: 1000 },
  club: null,
  categorie: 'Senior 1 Homme',
  dette: { depuis: null },
  nb_inscriptions: 1,
}

const LE_GALL: LignePaiementArcher = {
  archer_id: 3,
  nom: 'LE GALL',
  prenom: 'Anne',
  club_id: 4,
  recap: { du_centimes: 1200, paye_centimes: 1200, reste_centimes: 0 },
  club: 'Kervignac',
  categorie: 'Senior 1 Femme',
  dette: null,
  nb_inscriptions: 1,
}

// Inscrite au tournoi, à aucun créneau : elle doit 0, comme un créneau gratuit, sans en être un.
const RIOU: LignePaiementArcher = {
  archer_id: 4,
  nom: 'RIOU',
  prenom: 'Claire',
  club_id: null,
  recap: { du_centimes: 0, paye_centimes: 0, reste_centimes: 0 },
  club: null,
  categorie: 'Senior 1 Femme',
  dette: null,
  nb_inscriptions: 0,
}

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <Paiements tournoiId={1} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(getCompletude).mockResolvedValue(COMPLETUDE)
  vi.mocked(getPaiementsArchers).mockResolvedValue([MARTIN, DURAND, LE_GALL, RIOU])
  vi.mocked(getPaiementsClubs).mockResolvedValue([])
  vi.mocked(getRemboursements).mockResolvedValue([])
})

function cellulesDe(nom: string): (string | null)[] {
  const ligne = screen.getByText(new RegExp(`^${nom} `)).closest('tr')
  if (ligne === null) throw new Error(`« ${nom} » n’est pas dans une ligne de tableau`)
  return within(ligne)
    .getAllByRole('cell')
    .map((td) => td.textContent)
}

describe('paiements en carte-tableau (A17)', () => {
  it('un archer inscrit à aucun créneau n’a pas un tarif « Gratuit »', async () => {
    monter()

    await screen.findByRole('table')
    expect(cellulesDe('RIOU')[3]).toBe('aucun créneau')
  })

  it('CA — le bandeau porte attendu, encaissé, restant dû et archers concernés', async () => {
    monter()

    const bandeau = await screen.findByRole('group', { name: 'Totaux du tournoi' })
    const paires = within(bandeau)
      .getAllByRole('term')
      .map((dt) => [dt.textContent, dt.nextElementSibling?.textContent])
    expect(paires).toEqual([
      ['Attendu', '36,00 €'],
      ['Encaissé', '12,00 €'],
      ['Restant dû', '24,00 €'],
      ['Archers concernés', '2'],
    ])
  })

  it('CA — les colonnes de la planche, CLUB et CAT. nommés, l’ancienneté datée', async () => {
    monter()

    const table = await screen.findByRole('table')
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((th) => th.textContent),
    ).toEqual(['Archer', 'Club', 'Cat.', 'Tarif', 'Dû', 'Depuis', 'Action'])
    expect(cellulesDe('MARTIN').slice(0, 4)).toEqual([
      'MARTIN Sophie',
      'Kervignac',
      'Senior 1 Femme',
      '14,00 €',
    ])
    expect(cellulesDe('MARTIN')[5]).toBe('inscription du 02/11')
  })

  it('CA — une dette sans date se dit « date inconnue », jamais une case vide', async () => {
    monter()

    await screen.findByRole('table')
    expect(cellulesDe('DURAND')[5]).toBe('date inconnue')
    expect(cellulesDe('DURAND')[1]).toBe('sans club')
  })

  it('un archer à jour doit « 0,00 € », pas « Gratuit »', async () => {
    monter()

    await screen.findByRole('table')
    expect(cellulesDe('LE GALL')[4]).toMatch(/^0,00 €/)
  })
})
