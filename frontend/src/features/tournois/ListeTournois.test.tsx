// La liste des tournois en carte-tableau, planche A04 (E17US012) — tests écrits depuis le CA :
// `stories/E17-fidelite-aux-maquettes.md`, E17US012, puce « A04 » de l'arbitrage du 26/09/2026.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { TournoiEnListe } from '../competition/api'
import { getTournois } from '../competition/api'
import { getApercusJalon } from '../jalons/api'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import { GestionTournois } from './Tournois'

vi.mock('../competition/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../competition/api')>()),
  getTournois: vi.fn(),
}))

vi.mock('../jalons/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../jalons/api')>()),
  getApercusJalon: vi.fn(),
}))

const SALLE: TournoiEnListe = {
  id: 12,
  nom: 'Challenge des champions',
  date: '2026-11-22',
  lieu: 'Kervignac',
  type_tournoi: 'non_officiel',
  statut: 'en_cours',
  nb_inscrits: 156,
  nb_cibles: 30,
}

const SANS_SALLE: TournoiEnListe = {
  ...SALLE,
  id: 13,
  nom: 'Trophée d’hiver',
  statut: 'brouillon',
  nb_inscrits: 0,
  nb_cibles: null,
}

function monter(enfants: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{enfants}</QueryClientProvider>)
}

beforeEach(() => {
  vi.mocked(getTournois).mockResolvedValue([SALLE, SANS_SALLE])
  vi.mocked(getApercusJalon).mockResolvedValue([])
  useSessionAdminStore.setState({ jeton: 'jeton-de-test' })
})

function ligneDe(nom: string): HTMLElement {
  const ligne = screen.getByRole('button', { name: nom }).closest('tr')
  if (ligne === null) throw new Error(`« ${nom} » n’est pas dans une ligne de tableau`)
  return ligne
}

describe('liste des tournois en carte-tableau (A04)', () => {
  it('CA — un vrai <table> aux colonnes de la planche, sans les deux colonnes retirées', async () => {
    monter(
      <GestionTournois selectionneId={null} onChoisi={vi.fn()} ouvrir={null} onOuvrir={vi.fn()} />,
    )

    const table = await screen.findByRole('table')
    const colonnes = within(table)
      .getAllByRole('columnheader')
      .map((th) => th.textContent)
    expect(colonnes).toEqual(['État', 'Nom', 'Date', 'Inscrits', 'Cibles', 'Actions'])
  })

  it('CA — INSCRITS et CIBLES sont alimentées depuis la liste', async () => {
    monter(
      <GestionTournois selectionneId={null} onChoisi={vi.fn()} ouvrir={null} onOuvrir={vi.fn()} />,
    )

    await screen.findByRole('table')
    const cellules = within(ligneDe('Challenge des champions'))
      .getAllByRole('cell')
      .map((td) => td.textContent)
    expect(cellules.slice(2, 5)).toEqual(['2026-11-22', '156', '30'])
  })

  it('CA — sans plan de salle, CIBLES le dit plutôt que d’afficher une case vide ou 0', async () => {
    monter(
      <GestionTournois selectionneId={null} onChoisi={vi.fn()} ouvrir={null} onOuvrir={vi.fn()} />,
    )

    await screen.findByRole('table')
    const cellules = within(ligneDe('Trophée d’hiver')).getAllByRole('cell')
    expect(cellules[4]).toHaveTextContent('aucun plan')
  })

  it('la porte publique garde son allure : ni effectifs ni actions (revue axe D)', async () => {
    monter(
      <GestionTournois
        selectionneId={null}
        onChoisi={vi.fn()}
        ouvrir={null}
        onOuvrir={vi.fn()}
        lectureSeule
      />,
    )

    const table = await screen.findByRole('table')
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((th) => th.textContent),
    ).toEqual(['État', 'Nom', 'Date'])
    expect(screen.queryByText('aucun plan')).toBeNull()
  })
})
