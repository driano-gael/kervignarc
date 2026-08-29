// Test de rendu de la **pastille de préparation** dans la liste des tournois (E16US010).
//
// ⚠️ **Monter l'écran, pas le composant** : la première leçon de `Completude.test.tsx` — un test
// qui monte `PastillePreparation` seule reste vert si on la retire de `Tournois.tsx`. C'est
// exactement le défaut de `DETTE-085`, que `tsc` ne voit pas.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Tournoi } from '../competition/api'
import type { ApercuJalon } from '../jalons/api'
import { getApercusJalon } from '../jalons/api'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import { getTournois } from '../competition/api'
import { GestionTournois } from './Tournois'

vi.mock('../competition/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../competition/api')>()),
  getTournois: vi.fn(),
}))

vi.mock('../jalons/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../jalons/api')>()),
  getApercusJalon: vi.fn(),
}))

const BROUILLON: Tournoi = {
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

function apercu(niveau: ApercuJalon['niveau'], resume: string | null): ApercuJalon {
  return { tournoi_id: 12, niveau, resume }
}

beforeEach(() => {
  vi.mocked(getTournois).mockResolvedValue([BROUILLON])
  vi.mocked(getApercusJalon).mockReset()
  useSessionAdminStore.setState({ jeton: 'jeton-de-test' })
})

describe('pastille de préparation en liste', () => {
  it('CA A02 — « impossible de lancer en l’état » monte en alerte forte, avec sa cause', async () => {
    vi.mocked(getApercusJalon).mockResolvedValue([
      apercu('alerte', 'Un tournoi sans créneau ne peut pas être marqué prêt.'),
    ])

    monter(<GestionTournois selectionneId={null} onChoisi={vi.fn()} />)

    const pastille = await screen.findByText('Ne peut pas démarrer')
    expect(pastille).toHaveClass('badge-preparation--alerte')
    // `D-16` : la cause voyage jusqu'à l'écran, elle ne s'arrête pas au serveur.
    expect(pastille).toHaveAttribute(
      'title',
      'Un tournoi sans créneau ne peut pas être marqué prêt.',
    )
  })

  it('CA A02 — « tout n’est pas complet » reste un avertissement', async () => {
    vi.mocked(getApercusJalon).mockResolvedValue([
      apercu('avertissement', 'Il reste à préparer : Déroulé composé.'),
    ])

    monter(<GestionTournois selectionneId={null} onChoisi={vi.fn()} />)

    expect(await screen.findByText('À compléter')).toHaveClass('badge-preparation--avertissement')
  })

  it('un tournoi que rien ne retient ne porte AUCUNE pastille', async () => {
    // Assertion négative appariée aux deux positives ci-dessus : une pastille sur tous les
    // tournois ne dirait plus rien.
    vi.mocked(getApercusJalon).mockResolvedValue([apercu('aucun', null)])

    monter(<GestionTournois selectionneId={null} onChoisi={vi.fn()} />)

    await screen.findByText(/Salle 18m/)
    expect(screen.queryByText('Ne peut pas démarrer')).not.toBeInTheDocument()
    expect(screen.queryByText('À compléter')).not.toBeInTheDocument()
  })

  it('sans session admin, l’aperçu n’est même pas demandé', async () => {
    // La liste est rendue **aussi** sous la porte Public : sans ce garde, chaque affichage public
    // partait en 401.
    useSessionAdminStore.setState({ jeton: null })

    monter(<GestionTournois selectionneId={null} onChoisi={vi.fn()} />)

    await screen.findByText(/Salle 18m/)
    expect(getApercusJalon).not.toHaveBeenCalled()
  })
})
