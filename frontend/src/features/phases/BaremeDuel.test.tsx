// Le barème des duels sur l'écran des phases (E01US011). Monte `Phases` en entier : ce qu'on garde
// est « le réglage choisi part au serveur », pas « le contrôle sait s'afficher ».

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Categorie } from '../categories/api'
import type { ConfigPhase } from './api'
import { getCategories } from '../categories/api'
import { ajouterPhase, getPhases } from './api'
import { Phases } from './Phases'

vi.mock('./api', () => ({
  getPhases: vi.fn(),
  getAvancement: vi.fn(async () => []),
  ajouterPhase: vi.fn(),
  modifierPhase: vi.fn(),
  reordonnerPhases: vi.fn(),
  supprimerPhase: vi.fn(),
  changerStatutPhase: vi.fn(),
}))

vi.mock('../categories/api', () => ({ getCategories: vi.fn() }))

beforeEach(() => {
  vi.mocked(ajouterPhase).mockClear()
  vi.mocked(getCategories).mockResolvedValue([
    { id: 1, arme: 'Arc classique' } as Categorie,
    { id: 2, arme: 'Arc à poulies' } as Categorie,
  ])
})

function monter() {
  vi.mocked(getPhases).mockResolvedValue([])
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<Phases tournoiId={1} />, { wrapper: Enveloppe })
}

function configEnvoyee(): ConfigPhase {
  const appel = vi.mocked(ajouterPhase).mock.calls[0]
  if (appel === undefined) throw new Error('aucun POST de phase n’a été émis')
  return appel[1]
}

describe('le barème des duels d’une phase', () => {
  it('le preset club part au serveur, poulies au cumul d’après les armes du tournoi', async () => {
    monter()
    const preset = await screen.findByRole('button', { name: 'Preset format club' })
    // Le preset attend les armes (sinon il oublierait les poulies) : un seul clic, une fois actif.
    await waitFor(() => expect(preset).toBeEnabled())
    await userEvent.click(preset)
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter la phase' }))

    await waitFor(() => expect(ajouterPhase).toHaveBeenCalled())
    expect(configEnvoyee().bareme_duel).toEqual({
      par_defaut: { mode: 'sets', nb_manches: 5, nb_fleches_par_volee: 3, points_pour_gagner: 4 },
      surcharges: [
        {
          arme: 'Arc à poulies',
          bareme: { mode: 'cumul', nb_manches: 5, nb_fleches_par_volee: 3, points_pour_gagner: 0 },
        },
      ],
    })
  })

  it('les presets attendent les armes des catégories, et le disent', async () => {
    vi.mocked(getCategories).mockReturnValue(new Promise(() => {}))
    monter()

    expect(await screen.findByRole('button', { name: 'Preset format club' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Preset FFTA officiel' })).toBeDisabled()
    expect(screen.getByText(/Chargement des armes/)).toBeInTheDocument()
  })

  it('si les armes ne se chargent pas, les presets restent coupés et l’écran le dit', async () => {
    vi.mocked(getCategories).mockRejectedValue(new Error('réseau'))
    monter()

    expect(await screen.findByText(/Armes des catégories indisponibles/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Preset FFTA officiel' })).toBeDisabled()
    expect(screen.queryByText(/Chargement des armes/)).toBeNull()
  })

  it('signale un arc à poulies sans barème propre, puis une surcharge sans catégorie', async () => {
    monter()
    const fiche = await screen.findByRole('group', { name: 'Barème des duels' })
    const preset = within(fiche).getByRole('button', { name: 'Preset FFTA officiel' })
    await waitFor(() => expect(preset).toBeEnabled())
    await userEvent.click(preset)
    expect(within(fiche).queryByText(/Sans barème propre/)).toBeNull()

    await userEvent.click(
      within(fiche).getByRole('button', { name: /Retirer la surcharge de l’arme Arc à poulies/ }),
    )
    expect(within(fiche).getByText(/Sans barème propre/)).toHaveTextContent('Arc à poulies')

    await userEvent.click(
      within(fiche).getByRole('button', { name: 'Ajouter une arme au barème propre' }),
    )
    await userEvent.type(within(fiche).getByRole('combobox', { name: 'Arme' }), 'Arbalète')
    expect(within(fiche).getByText(/Aucune catégorie du tournoi/)).toHaveTextContent('Arbalète')
  })

  it('sans réglage, la phase part avec bareme_duel null (défaut du serveur, CA 3)', async () => {
    monter()
    await screen.findByRole('group', { name: 'Barème des duels' })
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter la phase' }))

    await waitFor(() => expect(ajouterPhase).toHaveBeenCalled())
    expect(configEnvoyee().bareme_duel).toBeNull()
  })

  it('une phase sans duel ne propose pas le réglage et n’envoie rien', async () => {
    monter()
    await screen.findByRole('group', { name: 'Barème des duels' })
    await userEvent.selectOptions(screen.getByLabelText(/Type de la phase/), 'echauffement')

    expect(screen.queryByRole('group', { name: 'Barème des duels' })).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter la phase' }))
    await waitFor(() => expect(ajouterPhase).toHaveBeenCalled())
    expect(configEnvoyee().bareme_duel).toBeNull()
  })

  it('un seuil inatteignable bloque l’ajout et dit pourquoi', async () => {
    monter()
    await userEvent.click(await screen.findByRole('button', { name: 'Preset FFTA officiel' }))
    const points = screen.getByRole('textbox', { name: 'Points pour gagner' })
    await userEvent.clear(points)
    await userEvent.type(points, '11')

    expect(screen.getByRole('button', { name: 'Ajouter la phase' })).toBeDisabled()
    const fiche = screen.getByRole('group', { name: 'Barème des duels' })
    expect(within(fiche).getByRole('status')).toHaveTextContent(/seuil atteignable/)
  })
})
