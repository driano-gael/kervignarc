// Suppression d'un tournoi peuplé : signaler, puis confirmer (E01US026, ADR-0077).
//
// ⚠️ **Monter l'écran, pas le dialogue** : un test qui monterait `DialogueConfirmation` seule
// resterait vert si on la retirait de `Tournois.tsx` — la leçon de `DETTE-085`, que `tsc` ne voit
// pas. Le décompte est **rendu par le serveur** : ces tests le simulent par un 409 typé, jamais en
// recalculant un chiffre côté client.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import type { Tournoi } from '../competition/api'
import { getTournois, supprimerTournoi } from '../competition/api'
import { getApercusJalon } from '../jalons/api'
import { GestionTournois } from './Tournois'

vi.mock('../competition/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../competition/api')>()),
  getTournois: vi.fn(),
  supprimerTournoi: vi.fn(),
}))

vi.mock('../jalons/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../jalons/api')>()),
  getApercusJalon: vi.fn(),
}))

const TERMINE: Tournoi = {
  id: 12,
  nom: 'Salle 18m',
  date: '2026-03-14',
  lieu: 'Kervignarc',
  type_tournoi: 'non_officiel',
  statut: 'termine',
}

const SIGNALEMENT =
  '« Salle 18m » porte 42 archers, 118 inscriptions et 3 remboursements (45,50 € encaissés, ' +
  'effacés sans contrepartie). Tout sera détruit et rien ne pourra être récupéré ; confirmez ' +
  'pour supprimer quand même.'

function monter(enfants: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{enfants}</QueryClientProvider>)
}

function peuple() {
  return new ErreurApi(409, 'tournoi_peuple', SIGNALEMENT)
}

beforeEach(() => {
  vi.mocked(getTournois).mockResolvedValue([TERMINE])
  vi.mocked(getApercusJalon).mockResolvedValue([])
  vi.mocked(supprimerTournoi).mockReset()
  useSessionAdminStore.setState({ jeton: 'jeton-de-test' })
})

describe('supprimer un tournoi peuplé', () => {
  it('CA — le décompte chiffré du serveur s’affiche dans le dialogue, pas en bandeau d’erreur', async () => {
    vi.mocked(supprimerTournoi).mockRejectedValue(peuple())
    monter(
      <GestionTournois
        selectionneId={null}
        onChoisi={() => {}}
        ouvrir={null}
        onOuvrir={() => {}}
      />,
    )
    await userEvent.click(await screen.findByRole('button', { name: 'Supprimer' }))

    const dialogue = await screen.findByRole('dialog')
    expect(dialogue).toHaveTextContent('42 archers')
    expect(dialogue).toHaveTextContent('118 inscriptions')
    expect(dialogue).toHaveTextContent('45,50 €')
    // Le signalement est une **question**, pas une panne : il ne doit pas doubler en bandeau rouge.
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('CA — la confirmation rejoue la suppression avec le drapeau, une seule fois', async () => {
    vi.mocked(supprimerTournoi).mockRejectedValueOnce(peuple()).mockResolvedValueOnce(undefined)
    monter(
      <GestionTournois
        selectionneId={null}
        onChoisi={() => {}}
        ouvrir={null}
        onOuvrir={() => {}}
      />,
    )
    await userEvent.click(await screen.findByRole('button', { name: 'Supprimer' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Supprimer définitivement' }))

    expect(supprimerTournoi).toHaveBeenNthCalledWith(1, 12, undefined)
    expect(supprimerTournoi).toHaveBeenNthCalledWith(2, 12, true)
  })

  it('CA — renoncer referme le dialogue sans rien supprimer', async () => {
    vi.mocked(supprimerTournoi).mockRejectedValue(peuple())
    monter(
      <GestionTournois
        selectionneId={null}
        onChoisi={() => {}}
        ouvrir={null}
        onOuvrir={() => {}}
      />,
    )
    await userEvent.click(await screen.findByRole('button', { name: 'Supprimer' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Annuler' }))

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(supprimerTournoi).toHaveBeenCalledTimes(1)
  })

  it('CA — un tournoi en cours n’offre PAS le bouton : le refus est définitif, pas confirmable', async () => {
    vi.mocked(getTournois).mockResolvedValue([{ ...TERMINE, statut: 'en_cours' }])
    monter(
      <GestionTournois
        selectionneId={null}
        onChoisi={() => {}}
        ouvrir={null}
        onOuvrir={() => {}}
      />,
    )

    expect(await screen.findByText(/Terminez ou annulez/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Supprimer' })).toBeNull()
  })

  it('un tournoi vide part sans aucune question — la confirmation doit rester rare', async () => {
    vi.mocked(supprimerTournoi).mockResolvedValue(undefined)
    monter(
      <GestionTournois
        selectionneId={null}
        onChoisi={() => {}}
        ouvrir={null}
        onOuvrir={() => {}}
      />,
    )
    await userEvent.click(await screen.findByRole('button', { name: 'Supprimer' }))

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(supprimerTournoi).toHaveBeenCalledWith(12, undefined)
  })
})
