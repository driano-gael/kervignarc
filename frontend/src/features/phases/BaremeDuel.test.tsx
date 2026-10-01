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
    await userEvent.click(preset)
    // Les armes arrivent par une requête : on attend qu'elles soient proposées, puis on rejoue
    // le preset pour qu'il en tienne compte.
    await waitFor(() =>
      expect(
        document.querySelector('#armes-bareme-duel option[value="Arc à poulies"]'),
      ).not.toBeNull(),
    )
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
