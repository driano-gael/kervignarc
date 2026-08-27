// Test de **rendu** de la liste d'affectations projetée (E16US009, correctif de 3ᵉ passe de revue).
//
// ⚠️ **Pourquoi ce fichier n'existait pas, et pourquoi c'est un défaut.** Le réglage de pages
// traverse `EcranSalle` → `VueDeSalle` → `VueAffectations` → `SalleParPages`. Les deux passes
// précédentes ont épinglé le **câblage** (le témoin d'`EcranSalle.test.tsx` recopie la prop) et la
// vue jumelle (`TableClassement.test.tsx` monte le vrai composant). Ici, rien : `features/routage/`
// n'avait que `presentation.test.ts`, qui teste des fonctions pures.
//
// Conséquence mesurée : supprimer `pagination?.noms_par_page` de `SalleParPages` laissait **toute
// la suite verte**, et la liste projetée retombait en silence sur `NOMS_PAR_PAGE = 40` /
// `SECONDES_PAR_PAGE = 20` — c'est-à-dire la moitié « affectations » du CA « la cadence et la
// taille d'une page se règlent par écran », perdue sans un seul signal. Un témoin mocké ne peut
// structurellement pas voir cela : il prouve qu'une prop **passe**, jamais qu'elle est
// **consommée**. C'est le mode de défaillance de `DETTE-085`, et le raisonnement n'avait été
// appliqué qu'à une des deux vues paginées.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useDeparts } from '../departs/hooks'
import { __reinitialiserCumulsDePage_TESTS } from '../../shared/ui/pagination'
import type { RoutageArcher } from './api'
import { useAffectations } from './hooks'
import { VueAffectations } from './VueAffectations'

// On mocke **les hooks** et non les fonctions de requête : `useAffectations` appelle sa fabrique par
// sa liaison locale au module, que le remplacement de l'export ne redirige pas (le piège déjà payé
// dans `TableClassement.test.tsx`, où le test lisait « connexion perdue »).
vi.mock('./hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./hooks')>()),
  useAffectations: vi.fn(),
}))
vi.mock('../departs/hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/hooks')>()),
  useDeparts: vi.fn(),
}))

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

function archer(i: number): RoutageArcher {
  return {
    archer_id: i,
    // Numéroté sur deux chiffres : le tri de `SalleParPages` est alphabétique, et « ARCHER10 »
    // passerait avant « ARCHER2 » — l'assertion porterait alors sur une page qu'on n'a pas voulue.
    nom: `ARCHER${String(i).padStart(2, '0')}`,
    prenom: 'Luc',
    issue: 'en_attente',
    prochain: null,
    prochaine_manche: null,
    rang_final: null,
    rang_min: null,
    rang_max: null,
    tour_sortie: null,
    destination: null,
    motif: null,
  }
}

const VINGT = Array.from({ length: 20 }, (_, i) => archer(i + 1))

describe('VueAffectations — la liste projetée honore le réglage de l’écran', () => {
  beforeEach(() => {
    __reinitialiserCumulsDePage_TESTS()
    vi.mocked(useDeparts).mockReturnValue({
      data: [{ id: 3, tournoi_id: 1, numero: 1, horaire: '09:00', etat: 'lance' }],
      isSuccess: true,
      isPending: false,
      isError: false,
      // Double cast **assumé** (règle 4-front) : le retour de React Query compte une trentaine de
      // champs dont aucun n'intervient ici. C'est un double de test, pas une valeur de production.
    } as unknown as ReturnType<typeof useDeparts>)
    vi.mocked(useAffectations).mockReturnValue({
      // Aucune butte posée : `SalleParPages` n'ajoute alors pas sa page « tour en cours », ce qui
      // rend le compteur directement lisible comme un nombre de pages de NOMS.
      data: { phase_id: 7, archers: VINGT },
      isSuccess: true,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useAffectations>)
  })

  it('découpe la page au nombre de noms RÉGLÉ, et non au défaut du module', () => {
    // 20 archers, 6 noms par page → 4 pages. Avec le défaut (40), il n'y en aurait qu'une, et les
    // vingt noms seraient rendus d'un coup : les deux assertions ci-dessous tombent.
    const { container } = render(
      <Cadre
        enfants={
          <VueAffectations
            tournoiId={1}
            interactif={false}
            pagination={{ noms_par_page: 6, cadence_page_s: 5 }}
          />
        }
      />,
    )

    expect(container.querySelectorAll('.salle-pages__nom')).toHaveLength(6)
    expect(container.querySelector('.salle-pages__compteur-total')?.textContent).toBe('/4')
  })

  it('retombe sur les défauts du module quand aucun réglage n’est servi', () => {
    // L'assertion **appariée** : sans elle, le test précédent passerait aussi avec un composant qui
    // paginerait à 6 en toutes circonstances. C'est aussi la non-régression d'avant l'US — un écran
    // qui n'a jamais été réglé doit se comporter exactement comme avant.
    const { container } = render(
      <Cadre enfants={<VueAffectations tournoiId={1} interactif={false} />} />,
    )

    // 20 archers tiennent dans une page de 40 : tout le monde est rendu, et le compteur disparaît.
    expect(container.querySelectorAll('.salle-pages__nom')).toHaveLength(20)
    expect(container.querySelector('.salle-pages__compteur')).toBeNull()
  })
})
