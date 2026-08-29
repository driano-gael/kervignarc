// Tests de rendu de la **recherche transverse** (E16US010).
//
// ⚠️ Un test de rendu par écran, la leçon de `DETTE-085` : `tsc` ne voit pas une propriété
// fournie et jamais consommée. Ce qui se vérifie ici est ce qu'aucun type ne prouve — que le
// scope change avec l'axe, que le clic remonte de quoi **ouvrir** la fiche, et que la troncature
// est chiffrée (`D-16`).

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Recherche, ResultatRecherche } from './api'
import { chercher } from './api'
import { RechercheTransverse } from './RechercheTransverse'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  chercher: vi.fn(),
}))

// La place d'un archer tire départs et plans : neutralisés pour n'observer que la recherche.
vi.mock('../departs/hooks', () => ({
  useDeparts: () => ({ data: [], isLoading: false, isError: false }),
}))

const LEVEQUE: ResultatRecherche = {
  entite: 'archer',
  id: 57,
  libelle: 'Lévêque Jean',
  precision: 'Arc Club de Kervignarc · Salle 18m',
  // ⚠️ **12, pas le tournoi courant** : c'est tout l'enjeu du champ — la recherche hors pilotage
  // traverse les éditions.
  tournoi_id: 12,
}

function reponse(resultats: ResultatRecherche[], total = resultats.length): Recherche {
  return { resultats, total }
}

function monter(enfants: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{enfants}</QueryClientProvider>)
}

beforeEach(() => {
  vi.mocked(chercher).mockReset()
  vi.mocked(chercher).mockResolvedValue(reponse([LEVEQUE]))
})

describe('RechercheTransverse', () => {
  it('CA — la déroulante propose les trois entités cherchables', () => {
    monter(<RechercheTransverse tournoiId={3} enPilotage={false} onOuvrir={vi.fn()} />)

    const deroulante = screen.getByLabelText('Rechercher')
    expect(deroulante).toHaveTextContent('Archer')
    expect(deroulante).toHaveTextContent('Tournoi')
    expect(deroulante).toHaveTextContent('Club')
  })

  it('CA — cliquer un résultat remonte de quoi OUVRIR sa fiche, tournoi compris', async () => {
    // Sans `tournoi_id`, la coquille ouvrirait la fiche dans le tournoi courant — donc vide.
    const onOuvrir = vi.fn()
    monter(<RechercheTransverse tournoiId={3} enPilotage={false} onOuvrir={onOuvrir} />)

    await userEvent.type(screen.getByLabelText('Archer à trouver'), 'leveque')
    await userEvent.click(await screen.findByRole('button', { name: /Lévêque Jean/ }))

    expect(onOuvrir).toHaveBeenCalledWith(LEVEQUE)
  })

  it('CA A09 — en pilotage la recherche d’archer se scope au tournoi courant', async () => {
    monter(<RechercheTransverse tournoiId={3} enPilotage={true} onOuvrir={vi.fn()} />)

    await userEvent.type(screen.getByLabelText('Archer à trouver'), 'lev')

    // `waitFor` porte aussi l'anti-rebond (`useValeurRetardee`) : la requête ne part qu'après.
    await waitFor(() => expect(chercher).toHaveBeenCalledWith('archer', 'lev', 3))
  })

  it('hors pilotage elle ne se scope PAS — sinon elle ne traverserait aucune édition', async () => {
    // Assertion négative appariée à la positive ci-dessus : sans elle, un scope toujours nul
    // rendrait les deux tests verts pour la mauvaise raison.
    monter(<RechercheTransverse tournoiId={3} enPilotage={false} onOuvrir={vi.fn()} />)

    await userEvent.type(screen.getByLabelText('Archer à trouver'), 'lev')

    await waitFor(() => expect(chercher).toHaveBeenCalledWith('archer', 'lev', null))
  })

  it('D-16 — une liste tronquée annonce son total, elle ne se tait pas', async () => {
    vi.mocked(chercher).mockResolvedValue(reponse([LEVEQUE], 34))
    monter(<RechercheTransverse tournoiId={3} enPilotage={false} onOuvrir={vi.fn()} />)

    await userEvent.type(screen.getByLabelText('Archer à trouver'), 'lev')

    expect(await screen.findByText(/1 sur 34/)).toBeInTheDocument()
  })

  it('une liste complète n’annonce aucun total — le bruit serait permanent', async () => {
    monter(<RechercheTransverse tournoiId={3} enPilotage={false} onOuvrir={vi.fn()} />)

    await userEvent.type(screen.getByLabelText('Archer à trouver'), 'lev')
    await screen.findByRole('button', { name: /Lévêque Jean/ })

    expect(screen.queryByText(/sur 1 —/)).not.toBeInTheDocument()
  })
})

describe('« il tire là » (E12US006, D-09)', () => {
  it('la place se rend pour un archer DU TOURNOI COURANT, y compris hors pilotage', async () => {
    // ⚠️ La régression corrigée : la place était liée au *scope de recherche*, donc absente de
    // l'axe Gestion où l'ancien composant la rendait. Le test l'exige sur `enPilotage={false}`.
    monter(<RechercheTransverse tournoiId={12} enPilotage={false} onOuvrir={vi.fn()} />)

    await userEvent.type(screen.getByLabelText('Archer à trouver'), 'lev')

    expect(await screen.findByText('Pas encore placé.')).toBeVisible()
  })

  it('mais PAS pour un archer d’une autre édition — ses plans ne sont pas ceux affichés', async () => {
    // Négatif apparié : sans lui, une place calculée sur le plan du tournoi courant serait
    // affichée pour un archer qui n'y tire pas — plausible et faux.
    monter(<RechercheTransverse tournoiId={3} enPilotage={false} onOuvrir={vi.fn()} />)

    await userEvent.type(screen.getByLabelText('Archer à trouver'), 'lev')
    await screen.findByRole('button', { name: /Lévêque Jean/ })

    expect(screen.queryByText('Pas encore placé.')).not.toBeInTheDocument()
  })
})

describe('anti-rebond', () => {
  it('DETTE-092 — une frappe rapide ne produit qu’UNE requête, sur la valeur finale', async () => {
    // ⚠️ **Horloge maîtrisée** (règle 9) : la 1ʳᵉ rédaction comparait la vitesse de frappe réelle à
    // la fenêtre de 250 ms, avec `toBeLessThan(4)` pour tolérance — trois requêtes sur sept
    // seraient passées, et un runner chargé l'aurait fait rougir sans régression. L'oracle est
    // désormais exact, et il porte aussi sur **la valeur** : un retard qui figerait la première
    // frappe passerait un simple décompte.
    // `shouldAdvanceTime` : React Query pose ses propres minuteurs, un gel total les fige aussi.
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const utilisateur = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    monter(<RechercheTransverse tournoiId={3} enPilotage={false} onOuvrir={vi.fn()} />)

    await utilisateur.type(screen.getByLabelText('Archer à trouver'), 'leveque')
    await act(async () => {
      vi.advanceTimersByTime(300)
    })

    expect(chercher).toHaveBeenCalledTimes(1)
    expect(chercher).toHaveBeenLastCalledWith('archer', 'leveque', null)
    vi.useRealTimers()
  })
})
