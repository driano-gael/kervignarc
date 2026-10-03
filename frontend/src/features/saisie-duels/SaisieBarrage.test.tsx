// Le pavé de barrage d'un duel (E13US003, CA 3 et 5) : `nb_fleches_barrage` flèches par camp, le
// plus haut total, puis la désignation du plus près du centre. Aucun test ne l'ouvrait avant.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Duel } from './api'
import { DuelCharge } from './SaisieDuels'

const mutate = vi.fn()
const MUTATION = { mutate, isPending: false, isError: false, error: null }

vi.mock('./hooks', () => ({
  useSaisirManche: () => MUTATION,
  useSaisirBarrage: () => MUTATION,
  useValiderDuel: () => MUTATION,
}))

function duelAEgalite(nbFlechesBarrage: number): Duel {
  return {
    numero: 1,
    tour: 1,
    place_en_jeu: null,
    haut: { archer_id: 11, nom: 'ALPHA', prenom: 'Équipe' },
    bas: { archer_id: 22, nom: 'BRAVO', prenom: 'Équipe' },
    est_bye: false,
    mode: 'sets',
    nb_manches: 4,
    nb_fleches_par_volee: 6,
    points_pour_gagner: 5,
    nb_fleches_barrage: nbFlechesBarrage,
    zones: ['10', '9', '8', 'M'],
    validee_par: null,
    manches: [],
    barrage: null,
    resultat: {
      points_haut: 4,
      points_bas: 4,
      vainqueur: null,
      termine: false,
      barrage_requis: true,
    },
  }
}

function monter(duel: Duel) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<DuelCharge tournoiId={1} phaseId={2} matchNumero={1} duel={duel} onValide={() => {}} />, {
    wrapper: Enveloppe,
  })
}

async function tirer(camp: string, zones: string[]) {
  const groupe = screen.getByRole('group', { name: `Flèches de barrage de ${camp}` })
  for (const zone of zones)
    await userEvent.click(within(groupe).getByRole('button', { name: zone }))
}

describe('barrage d’équipe à trois flèches', () => {
  beforeEach(() => mutate.mockClear())

  it('envoie les trois flèches de chaque camp ; le plus haut total suffit', async () => {
    monter(duelAEgalite(3))
    await tirer('ALPHA', ['10', '9', '9'])
    await tirer('BRAVO', ['9', '9', '9'])

    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer le barrage' }))

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        fleches_haut: ['10', '9', '9'],
        fleches_bas: ['9', '9', '9'],
        gagnant_designe: null,
      }),
    )
  })

  it('n’accepte pas une quatrième flèche, et « Effacer » retire la dernière', async () => {
    monter(duelAEgalite(3))
    const alpha = screen.getByRole('group', { name: 'Flèches de barrage de ALPHA' })
    await tirer('ALPHA', ['10', '9', '8'])
    expect(within(alpha).getByRole('button', { name: '10' })).toBeDisabled()

    await userEvent.click(
      within(alpha).getByRole('button', { name: 'Effacer la dernière flèche de barrage de ALPHA' }),
    )
    await tirer('ALPHA', ['M'])
    await tirer('BRAVO', ['9', '9', '9'])
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer le barrage' }))

    expect(mutate).toHaveBeenCalledWith(expect.objectContaining({ fleches_haut: ['10', '9', 'M'] }))
  })

  it('à totaux égaux, exige la désignation du plus près du centre', async () => {
    monter(duelAEgalite(3))
    await tirer('ALPHA', ['10', '9', '8'])
    await tirer('BRAVO', ['9', '9', '9'])
    const enregistrer = screen.getByRole('button', { name: 'Enregistrer le barrage' })
    expect(enregistrer).toBeDisabled()

    const designation = screen.getByRole('group', { name: 'Plus près du centre' })
    await userEvent.click(within(designation).getByRole('button', { name: 'BRAVO' }))
    await userEvent.click(enregistrer)

    expect(mutate).toHaveBeenCalledWith(expect.objectContaining({ gagnant_designe: 'bas' }))
  })

  it('une correction de flèche efface la désignation : elle se redemande', async () => {
    monter(duelAEgalite(3))
    await tirer('ALPHA', ['10', '9', '8'])
    await tirer('BRAVO', ['9', '9', '9'])
    const designation = screen.getByRole('group', { name: 'Plus près du centre' })
    await userEvent.click(within(designation).getByRole('button', { name: 'BRAVO' }))

    const alpha = screen.getByRole('group', { name: 'Flèches de barrage de ALPHA' })
    await userEvent.click(
      within(alpha).getByRole('button', { name: 'Effacer la dernière flèche de barrage de ALPHA' }),
    )
    await tirer('ALPHA', ['8'])

    expect(screen.getByRole('button', { name: 'Enregistrer le barrage' })).toBeDisabled()
  })

  it('reste incomplet tant qu’un camp n’a pas ses trois flèches', async () => {
    monter(duelAEgalite(3))
    await tirer('ALPHA', ['10', '9', '9'])
    await tirer('BRAVO', ['9', '9'])

    expect(screen.getByRole('button', { name: 'Enregistrer le barrage' })).toBeDisabled()
  })
})

describe('barrage individuel à une flèche (inchangé)', () => {
  beforeEach(() => mutate.mockClear())

  it('toucher une autre zone remplace la flèche au lieu de l’ajouter', async () => {
    monter(duelAEgalite(1))
    await tirer('ALPHA', ['10', '8'])
    await tirer('BRAVO', ['9'])

    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer le barrage' }))

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ fleches_haut: ['8'], fleches_bas: ['9'] }),
    )
  })
})
