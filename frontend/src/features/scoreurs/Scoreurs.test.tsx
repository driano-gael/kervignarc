// Révélation du QR d'un scoreur (E16US015, ADR-0105) — la **mesure de sécurité** de l'US.
//
// ⚠️ Ce fichier existe parce que la revue du 04/09/2026 a constaté qu'un CA porteur d'un arbitrage
// de sécurité était livré sans aucun test : le CA disait « le QR n'est pas seulement caché, il
// n'est pas demandé », et rien ne l'exécutait. Les assertions portent donc sur l'**appel réseau**
// (`getQrScoreur`) autant que sur le DOM — un QR absent de l'écran mais déjà chargé ne tiendrait
// pas la promesse faite au commanditaire.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { Scoreurs } from './Scoreurs'
import type { Scoreur } from './api'

const getQrScoreur = vi.fn()
let scoreursRendus: Scoreur[] = []

vi.mock('./api', () => ({
  getScoreurs: () => Promise.resolve(scoreursRendus),
  getQrScoreur: (tournoiId: number, scoreurId: number) => getQrScoreur(tournoiId, scoreurId),
  creerScoreur: vi.fn(),
  modifierScoreur: vi.fn(),
  supprimerScoreur: vi.fn(),
  telechargerCartesScoreurs: vi.fn(),
}))

let client: QueryClient

function monter() {
  // ⚠️ `staleTime` **doit refléter la production** (`app/queryClient.ts`, 30 s) : à 0, React Query
  // refetche à chaque montage et le test du cache devient vert quoi qu'il arrive — c'est le piège
  // dans lequel la 1ʳᵉ rédaction est tombée (2ᵉ passe de revue).
  client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 30_000 } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(<Scoreurs tournoiId={1} />, { wrapper: Enveloppe })
}

const QR_PAR_DEFAUT = 'data:image/svg+xml,%3Csvg%3E%3C%2Fsvg%3E'

const alice: Scoreur = { id: 1, tournoi_id: 1, nom: 'Alice', code: 'AAA222' }
const bob: Scoreur = { id: 2, tournoi_id: 1, nom: 'Bob', code: 'BBB333' }

describe('Scoreurs — le QR ne se montre que sur geste', () => {
  beforeEach(() => {
    getQrScoreur.mockReset()
    getQrScoreur.mockResolvedValue(QR_PAR_DEFAUT)
    scoreursRendus = [alice, bob]
  })

  it('ne demande aucun QR au montage de l’écran', async () => {
    monter()
    await screen.findByText('Alice')

    // L'assertion qui garde vraiment le CA : pas « rien n'est affiché », mais « rien n'a été
    // demandé ». Un écran qui préchargerait tous les QR les rendrait scannables d'un cliché.
    expect(getQrScoreur).not.toHaveBeenCalled()
    expect(screen.queryByRole('img')).toBeNull()
  })

  it('affiche le QR du scoreur demandé, et lui seul', async () => {
    monter()
    await userEvent.click(await screen.findByRole('button', { name: 'Afficher le QR de Alice' }))

    expect(getQrScoreur).toHaveBeenCalledTimes(1)
    expect(getQrScoreur).toHaveBeenCalledWith(1, alice.id)
    expect(await screen.findByAltText('QR de session de Alice')).toBeInTheDocument()
    expect(screen.queryByAltText('QR de session de Bob')).toBeNull()
  })

  it('n’en garde qu’un seul ouvert : ouvrir le second referme le premier', async () => {
    monter()
    await userEvent.click(await screen.findByRole('button', { name: 'Afficher le QR de Alice' }))
    await screen.findByAltText('QR de session de Alice')
    await userEvent.click(screen.getByRole('button', { name: 'Afficher le QR de Bob' }))

    expect(await screen.findByAltText('QR de session de Bob')).toBeInTheDocument()
    expect(screen.queryByAltText('QR de session de Alice')).toBeNull()
  })

  it('referme sur « Masquer le QR »', async () => {
    monter()
    await userEvent.click(await screen.findByRole('button', { name: 'Afficher le QR de Alice' }))
    await screen.findByAltText('QR de session de Alice')
    await userEvent.click(screen.getByRole('button', { name: 'Masquer le QR de Alice' }))

    expect(screen.queryByAltText('QR de session de Alice')).toBeNull()
  })

  it('ne rouvre AUCUN QR quand un id supprimé est réattribué à un scoreur neuf', async () => {
    // ⚠️ Bloquant relevé en revue le 04/09/2026. SQLite réattribue les `id` (PK sans
    // AUTOINCREMENT) : afficher le QR de Bob, supprimer Bob, créer Charlie lui donne l'id 2. Un
    // état indexé sur l'`id` rouvrait alors le QR de Charlie **sans clic** — et servait celui de
    // Bob depuis le cache. L'état est donc indexé sur le `code`, unique et jamais réémis.
    monter()
    await userEvent.click(await screen.findByRole('button', { name: 'Afficher le QR de Bob' }))
    await screen.findByAltText('QR de session de Bob')

    // ⚠️ On invalide la liste au lieu de re-rendre dans un provider neuf : envelopper `Scoreurs`
    // d'un niveau supplémentaire le **déplace dans l'arbre**, donc React le remonte et `qrOuvert`
    // repart à `null` — le test redevenait vert sur le code défectueux (piège de la 1ʳᵉ rédaction).
    const charlie: Scoreur = { id: bob.id, tournoi_id: 1, nom: 'Charlie', code: 'CCC444' }
    scoreursRendus = [alice, charlie]
    await client.invalidateQueries({ queryKey: ['scoreurs', 1] })

    expect(await screen.findByText('Charlie')).toBeInTheDocument()
    // ⚠️ L'assertion porte sur le **bouton**, pas sur l'image : l'image arrive de façon asynchrone,
    // donc `queryByAltText` est nul même quand le QR est ouvert. Le libellé du bouton, lui, est
    // rendu en même temps que la ligne — c'est la seule assertion qui discrimine.
    expect(screen.queryByRole('button', { name: /^Masquer le QR/ })).toBeNull()
    expect(screen.getAllByRole('button', { name: /^Afficher le QR/ })).toHaveLength(2)
  })

  it('ne sert PAS le QR du supprimé depuis le cache quand son id est réattribué', async () => {
    // ⚠️ 2ᵉ passe de revue : l'`id` avait été chassé de l'état d'ouverture mais **pas de la clé de
    // cache**. Sur `['qr-scoreur', t, id]`, rouvrir le QR du successeur servait le SVG révoqué du
    // supprimé. ⚠️ L'oracle est **l'image servie**, pas le compteur d'appels : revenir à une clé par
    // `id` en compensant par un `invalidateQueries` laisserait le compteur juste tout en affichant
    // le SVG périmé pendant le refetch de fond (3ᵉ passe).
    getQrScoreur.mockReset()
    getQrScoreur
      .mockResolvedValueOnce('data:image/svg+xml,bob')
      .mockResolvedValueOnce('data:image/svg+xml,charlie')
    monter()
    await userEvent.click(await screen.findByRole('button', { name: 'Afficher le QR de Bob' }))
    await screen.findByAltText('QR de session de Bob')
    await userEvent.click(screen.getByRole('button', { name: 'Masquer le QR de Bob' }))

    const charlie: Scoreur = { id: bob.id, tournoi_id: 1, nom: 'Charlie', code: 'CCC444' }
    scoreursRendus = [alice, charlie]
    await client.invalidateQueries({ queryKey: ['scoreurs', 1] })
    await screen.findByText('Charlie')
    await userEvent.click(screen.getByRole('button', { name: 'Afficher le QR de Charlie' }))

    expect(await screen.findByAltText('QR de session de Charlie')).toHaveAttribute(
      'src',
      'data:image/svg+xml,charlie',
    )
    expect(getQrScoreur).toHaveBeenCalledTimes(2)
  })

  it('ne transporte pas l’état d’une ligne supprimée sur celle qui hérite de son id', async () => {
    // ⚠️ La `key` de ligne gouverne l'état LOCAL (`edition`, `confirmationSuppression`). Sur
    // `key={scoreur.id}`, armer « Supprimer » sur Bob puis voir la liste revenir avec Charlie sur
    // l'id 2 laissait la ligne de Charlie **armée en confirmation** — un geste destructeur
    // transféré à une autre personne. La `key` porte donc le code (3ᵉ passe de revue).
    monter()
    await userEvent.click(await screen.findByRole('button', { name: 'Supprimer Bob' }))
    expect(
      screen.getByRole('button', { name: 'Confirmer la suppression de Bob' }),
    ).toBeInTheDocument()

    const charlie: Scoreur = { id: bob.id, tournoi_id: 1, nom: 'Charlie', code: 'CCC444' }
    scoreursRendus = [alice, charlie]
    await client.invalidateQueries({ queryKey: ['scoreurs', 1] })
    await screen.findByText('Charlie')

    expect(screen.getByRole('button', { name: 'Supprimer Charlie' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Confirmer la suppression/ })).toBeNull()
  })
})
