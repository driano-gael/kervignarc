// Garde-fou de l'ouverture pilotée par l'adresse (E16US010, ADR-0100 §4).
//
// ⚠️ Ce fichier existe parce qu'ADR-0100 affirmait le hook « gardé par `axes.test.ts` ». C'était
// faux : celui-ci garde la réciprocité du **parseur**, il ne touche jamais le hook. Nommer un
// module qui n'applique pas ce qu'on lui prête est le défaut qu'ADR-0075 documente.

// ⚠️ On monte l'ÉCRAN (`Archers`) avec ses props d'adresse, pas le hook seul : c'est la branche
// « adresse » qu'aucun test de rendu n'exerçait, les quatre écrans neufs étant tous montés sans
// `ouvrir`/`onOuvrir`, donc systématiquement dans le repli local.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Archer } from '../../features/archers/api'
import { getArchers, getDoublons } from '../../features/archers/api'
import { Archers } from '../../features/archers/Archers'

vi.mock('../../features/archers/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../features/archers/api')>()),
  getArchers: vi.fn(),
  getDoublons: vi.fn(),
}))
vi.mock('../../features/clubs/hooks', () => ({ useClubs: () => ({ data: [] }) }))
vi.mock('../../features/categories/hooks', () => ({ useCategories: () => ({ data: [] }) }))
vi.mock('../../features/blasons/hooks', () => ({ useBlasons: () => ({ data: [] }) }))

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

function monter(enfants: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{enfants}</QueryClientProvider>)
}

beforeEach(() => {
  vi.mocked(getArchers).mockResolvedValue([archer(57, 'Jean'), archer(58, 'Luc')])
  vi.mocked(getDoublons).mockResolvedValue([])
})

describe('ouverture pilotée par l’adresse', () => {
  it('l’archer désigné par l’adresse est déplié — et LUI SEUL', async () => {
    monter(<Archers tournoiId={1} ouvrir={57} onOuvrir={vi.fn()} />)

    // Le formulaire d'édition porte les champs ; les autres lignes gardent leur bouton « Modifier ».
    expect(await screen.findByDisplayValue('Jean')).toBeVisible()
    expect(screen.queryByDisplayValue('Luc')).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Modifier' })).toHaveLength(1)
  })

  it('sans élément dans l’adresse, aucune fiche n’est ouverte', async () => {
    // Négatif apparié : sans lui, un composant qui ouvrirait tout resterait vert au test ci-dessus.
    monter(<Archers tournoiId={1} ouvrir={null} onOuvrir={vi.fn()} />)

    await screen.findByText(/Dupont Jean/)
    expect(screen.queryByDisplayValue('Jean')).not.toBeInTheDocument()
  })

  it('la fermeture REMONTE à l’adresse au lieu de vivre en local', async () => {
    // C'est ce qui fait qu'il n'y a qu'une source : un état local se serait refermé tout seul, en
    // laissant l'adresse désigner une fiche close — et le même lien aurait cessé de la rouvrir.
    const onOuvrir = vi.fn()
    monter(<Archers tournoiId={1} ouvrir={57} onOuvrir={onOuvrir} />)

    await userEvent.click(await screen.findByRole('button', { name: 'Annuler' }))

    expect(onOuvrir).toHaveBeenCalledWith(null)
  })
})
