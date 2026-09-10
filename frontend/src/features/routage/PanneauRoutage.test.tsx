// Le retour automatique du panneau (E16US018) — test de **rendu**, pas de logique pure.
//
// ⚠️ Il porte le CA que `presentation.test.ts` ne peut pas prouver : le panneau se referme **quelle
// que soit l'issue de ses lignes**. Le cas nominal en duels mêle un `prochain_duel` et un `termine`
// — sous la règle « il reste dès qu'une ligne est terminale », écartée au cadrage, ce test serait
// rouge et l'US morte-née sur cet écran.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDeparts } from '../departs/hooks'
import type { RoutageArcher } from './api'
import { useRoutage } from './hooks'
import { PanneauRoutage } from './PanneauRoutage'
import { FERMETURE_MS } from './presentation'

// On mocke **les hooks**, jamais les fabriques de requête : `useRoutage` appelle la sienne par sa
// liaison locale au module, que le remplacement de l'export ne redirige pas.
vi.mock('./hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./hooks')>()),
  useRoutage: vi.fn(),
}))
vi.mock('../departs/hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/hooks')>()),
  useDeparts: vi.fn(),
}))

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

function archer(patch: Partial<RoutageArcher> = {}): RoutageArcher {
  return {
    archer_id: 1,
    nom: 'MARTIN',
    prenom: 'Luc',
    issue: 'prochain_duel',
    prochain: {
      numero: 3,
      tour: 2,
      libelle: 'Quart de finale',
      cible: 4,
      position: 'B',
      adversaire: null,
      sources_en_attente: [],
      manque: null,
      alerte: null,
    },
    prochaine_manche: null,
    rang_final: null,
    rang_min: null,
    rang_max: null,
    tour_sortie: null,
    destination: null,
    motif: null,
    ...patch,
  }
}

// Le duel qu'on vient de valider : un qui continue, un qui sort. C'est le cas **nominal**.
const DUEL_TRANCHE = [
  archer(),
  archer({
    archer_id: 2,
    nom: 'DURAND',
    prenom: 'Anne',
    issue: 'termine',
    prochain: null,
    rang_final: 3,
    rang_min: 3,
    rang_max: 3,
    tour_sortie: 'Demi-finale',
  }),
]

function monter(lignes: RoutageArcher[], onRetour: () => void, avisPermanent = false) {
  // ⚠️ `as unknown as ReturnType<…>` et non `as never` — patron du voisin `VueAffectations.test.tsx`.
  // `as never` désactive toute vérification de forme : si le hook changeait de contrat, le mock
  // cesserait de fournir `archers`, `lignes` retomberait à `[]` et le test « quelle que soit
  // l'issue » ne testerait plus rien — en restant vert.
  vi.mocked(useDeparts).mockReturnValue({
    data: [{ id: 7, numero: 1, statut: 'en_cours' }],
  } as unknown as ReturnType<typeof useDeparts>)
  vi.mocked(useRoutage).mockReturnValue({
    data: { phase_id: 9, archers: lignes, avis_permanent: avisPermanent },
    isLoading: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useRoutage>)
  render(
    <Cadre
      enfants={
        <PanneauRoutage
          tournoiId={1}
          archerIds={lignes.map((l) => l.archer_id)}
          titrePanneau="Où tire-t-on ensuite ?"
          onRetour={onRetour}
        />
      }
    />,
  )
}

describe('PanneauRoutage — retour automatique', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => {
    // ⚠️ `clearAllTimers` et non `runOnlyPendingTimers` : les `afterEach` s'exécutent en pile
    // inverse, donc **avant** le démontage de Testing Library. Faire battre l'horloge une fois de
    // plus sur un panneau vivant avance `maintenant` hors d'`act()` — inoffensif aujourd'hui, mais
    // le jour où un test se posera à une seconde de l'échéance, il basculera sans raison lisible.
    vi.clearAllTimers()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('rend la tablette au bout de trois minutes même quand une ligne est terminale', () => {
    const onRetour = vi.fn()
    monter(DUEL_TRANCHE, onRetour)
    expect(onRetour).not.toHaveBeenCalled()
    act(() => void vi.advanceTimersByTime(FERMETURE_MS))
    expect(onRetour).toHaveBeenCalledTimes(1)
  })

  it('ne rend pas la tablette avant l’échéance', () => {
    const onRetour = vi.fn()
    monter(DUEL_TRANCHE, onRetour)
    act(() => void vi.advanceTimersByTime(FERMETURE_MS - 5_000))
    expect(onRetour).not.toHaveBeenCalled()
  })

  it('ne rend la tablette qu’une fois, même si le battement continue', () => {
    // Le battement ne s'arrête pas de lui-même : sans garde, `onRetour` partirait à chaque seconde
    // au-delà de l'échéance, et en duels cela remonterait la liste des matchs en boucle.
    const onRetour = vi.fn()
    monter(DUEL_TRANCHE, onRetour)
    act(() => void vi.advanceTimersByTime(FERMETURE_MS + 5_000))
    expect(onRetour).toHaveBeenCalledTimes(1)
  })

  it('annonce le retour par un signal discret, sans compter les secondes', () => {
    monter(DUEL_TRANCHE, vi.fn())
    const signal = screen.getByRole('img', { name: /retour automatique/i })

    // ⚠️ L'assertion porte sur le **bloc entier**, jamais sur la seule barre : celle-ci n'a pas de
    // texte par construction, donc son `textContent` est vide quoi qu'on écrive à côté. La version
    // précédente serait restée verte si l'on avait ajouté « 2:41 » à la mention voisine —
    // c'est-à-dire précisément la variante C écartée au questionnaire S06 (relevé en revue).
    expect(signal.textContent ?? '').not.toMatch(/\d/)
    expect(signal.querySelector('[aria-valuenow]')).toBeNull()
  })

  it('ne referme pas un écriteau — une pause dure plus longtemps que trois minutes', () => {
    // ⚠️ « Tir suspendu : restez à disposition » vaut tant que la pause dure (15 à 20 min) ; le
    // minuteur l'emporterait au tiers. C'est le **serveur** qui distingue l'écriteau de l'annonce.
    const onRetour = vi.fn()
    const enPause = [
      archer({ issue: 'en_attente', prochain: null, motif: 'Tir suspendu… Restez à disposition.' }),
    ]
    monter(enPause, onRetour, true)

    act(() => void vi.advanceTimersByTime(FERMETURE_MS * 2))

    expect(onRetour).not.toHaveBeenCalled()
    expect(screen.queryByRole('img', { name: /retour automatique/i })).toBeNull()
  })
})
