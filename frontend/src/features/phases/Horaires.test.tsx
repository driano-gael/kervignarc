// La **durée prévue** et la **grille horaire**, sur l'écran des phases d'un tournoi (E03US010).
//
// Monte `Phases` en entier, comme `Titre.test.tsx` et pour sa raison : ce qu'on garde, c'est que
// l'organisateur puisse régler une durée sans effacer le reste (`PUT` total), et lire la grille.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ConfigPhase, EtapeDeroule, HorairesDepart } from './api'
import { getHorairesPrevus, getPhases, modifierPhase } from './api'
import { Phases } from './Phases'

vi.mock('./api', () => ({
  getPhases: vi.fn(),
  getHorairesPrevus: vi.fn(),
  getAvancement: vi.fn(async () => []),
  ajouterPhase: vi.fn(),
  modifierPhase: vi.fn(),
  reordonnerPhases: vi.fn(),
  supprimerPhase: vi.fn(),
  changerStatutPhase: vi.fn(),
}))

const TABLEAU: EtapeDeroule = {
  id: 7,
  tournoi_id: 1,
  ordre: 2,
  type: 'elimination_directe',
  sources: [],
  effectif: null,
  barrage_jusqu_au: null,
  profondeur: null,
  poules: null,
  big_shoot_off: null,
  suisse: null,
  bareme_duel: null,
  colline: null,
  decoupage: null,
  nb_volees: null,
  arrets: [],
  titre: null,
  duree_prevue: null,
}

const QUALIFICATION: EtapeDeroule = {
  ...TABLEAU,
  id: 8,
  ordre: 1,
  type: 'qualification',
  nb_volees: 20,
  titre: 'Qualif du matin',
}

beforeEach(() => {
  vi.mocked(modifierPhase).mockClear()
  vi.mocked(getHorairesPrevus).mockClear()
  vi.mocked(getHorairesPrevus).mockResolvedValue([])
})

function monter(phases: EtapeDeroule[]) {
  vi.mocked(getPhases).mockResolvedValue(phases)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<Phases tournoiId={1} />, { wrapper: Enveloppe })
}

function ligne(index: number) {
  const element = screen.getAllByRole('listitem').filter((el) => el.classList.contains('phase'))[
    index
  ]
  if (element === undefined) throw new Error(`Aucune ligne de phase au rang ${index}.`)
  return within(element)
}

function configEnvoyee(): ConfigPhase {
  const appel = vi.mocked(modifierPhase).mock.calls[0]
  if (appel === undefined) throw new Error('aucun PUT de phase n’a été émis')
  return appel[2]
}

async function ouvrirLaFiche(index: number) {
  await screen.findAllByRole('listitem')
  await userEvent.click(ligne(index).getByRole('button', { name: 'Ouvrir la fiche' }))
}

describe('la durée prévue d’une phase', () => {
  it('se règle sur la qualification sans effacer son titre (PUT total)', async () => {
    monter([QUALIFICATION, TABLEAU])
    await ouvrirLaFiche(0)

    await userEvent.type(ligne(0).getByLabelText(/Durée prévue/), '150')
    await userEvent.click(
      ligne(0).getByRole('button', { name: 'Enregistrer la durée prévue de la phase 1' }),
    )

    expect(configEnvoyee()).toMatchObject({ duree_prevue: 150, titre: 'Qualif du matin' })
  })

  it('rafraîchit la grille après l’enregistrement', async () => {
    vi.mocked(modifierPhase).mockResolvedValue(QUALIFICATION)
    monter([QUALIFICATION])
    await ouvrirLaFiche(0)
    await waitFor(() => expect(vi.mocked(getHorairesPrevus)).toHaveBeenCalledTimes(1))

    await userEvent.type(ligne(0).getByLabelText(/Durée prévue/), '150')
    await userEvent.click(
      ligne(0).getByRole('button', { name: 'Enregistrer la durée prévue de la phase 1' }),
    )

    await waitFor(() => expect(vi.mocked(getHorairesPrevus)).toHaveBeenCalledTimes(2))
  })

  it('refuse d’envoyer une durée que le serveur refuserait', async () => {
    monter([QUALIFICATION])
    await ouvrirLaFiche(0)

    await userEvent.type(ligne(0).getByLabelText(/Durée prévue/), '1.5')

    const bouton = ligne(0).getByRole('button', {
      name: 'Enregistrer la durée prévue de la phase 1',
    })
    expect(bouton).toBeDisabled()
    expect(ligne(0).getByText(/Un nombre entier de minutes, de 1 à 1440/)).toBeInTheDocument()
  })

  it('vidée, est envoyée à null : c’est le geste qui la retire', async () => {
    monter([{ ...QUALIFICATION, duree_prevue: 90 }])
    await ouvrirLaFiche(0)

    await userEvent.clear(ligne(0).getByLabelText(/Durée prévue/))
    await userEvent.click(
      ligne(0).getByRole('button', { name: 'Enregistrer la durée prévue de la phase 1' }),
    )

    expect(configEnvoyee().duree_prevue).toBeNull()
  })

  it('survit à l’édition d’un autre réglage dans le formulaire de la phase', async () => {
    monter([QUALIFICATION, { ...TABLEAU, duree_prevue: 45 }])
    await ouvrirLaFiche(1)

    await userEvent.click(ligne(1).getByRole('button', { name: 'Enregistrer' }))

    expect(configEnvoyee().duree_prevue).toBe(45)
  })

  it('reste réglable sur la qualification après un autre widget de la fiche', async () => {
    // `configInchangee` réémet la durée : régler le titre ne doit pas la perdre.
    monter([{ ...QUALIFICATION, duree_prevue: 120 }])
    await ouvrirLaFiche(0)

    await userEvent.click(ligne(0).getAllByRole('button', { name: 'Enregistrer' })[0]!)

    expect(configEnvoyee().duree_prevue).toBe(120)
  })
})

describe('la grille horaire', () => {
  const HORAIRES: HorairesDepart[] = [
    {
      depart_id: 11,
      numero: 1,
      horaire: '09:00',
      etapes: [
        {
          etape_id: 8,
          ordre: 1,
          debut: { heure: '09:00', jours_apres: 0 },
          fin: { heure: '11:30', jours_apres: 0 },
        },
        { etape_id: 7, ordre: 2, debut: { heure: '11:30', jours_apres: 0 }, fin: null },
      ],
    },
    {
      depart_id: 12,
      numero: 2,
      horaire: '22:00',
      etapes: [
        {
          etape_id: 8,
          ordre: 1,
          debut: { heure: '22:00', jours_apres: 0 },
          fin: { heure: '00:30', jours_apres: 1 },
        },
        { etape_id: 7, ordre: 2, debut: { heure: '00:30', jours_apres: 1 }, fin: null },
      ],
    },
  ]

  it('croise les phases et les départs, l’inconnu en tiret et le lendemain signalé', async () => {
    vi.mocked(getHorairesPrevus).mockResolvedValue(HORAIRES)
    monter([{ ...QUALIFICATION, duree_prevue: 150 }, TABLEAU])

    const grille = within(await screen.findByRole('table'))

    expect(grille.getByRole('columnheader', { name: 'Départ 2 (22:00)' })).toBeInTheDocument()
    const qualif = within(grille.getByRole('row', { name: /Qualif du matin/ }))
    expect(qualif.getByText('2 h 30')).toBeInTheDocument()
    expect(qualif.getByText('09:00 → 11:30')).toBeInTheDocument()
    expect(qualif.getByText('22:00 → 00:30 (lendemain)')).toBeInTheDocument()
    const tableau = within(grille.getByRole('row', { name: /Élimination directe/ }))
    expect(tableau.getByText('11:30 → —')).toBeInTheDocument()
    expect(tableau.getByText('00:30 (lendemain) → —')).toBeInTheDocument()
  })
})
