// Tests de **montage** de la vue « Suivi » (E07US006, élargie par E16US004).
//
// Ce fichier comble un angle mort relevé en 2ᵉ et 3ᵉ passes de revue : `VueSuivi` est le composant
// le plus modifié de l'US **et** l'onglet d'atterrissage de l'appli publique, et il n'avait aucun
// rendu testé. Sa logique extraite l'était (`suivi.test.ts`, `tableaux/presentation.test.ts`), son
// assemblage non.
//
// ⚠️ **La démonstration est arrivée d'elle-même, et vaut d'être écrite** : pendant la 3ᵉ passe, une
// erreur de syntaxe JSX a été introduite dans ce fichier de production — et **les 740 tests sont
// restés verts**. Rien ne montait `VueSuivi` : `AccueilPublic.test.tsx` le mocke, et aucun autre
// test ne l'importe. Seul `tsc` l'a vu. Un composant qui ne compile pas et dont la suite ne dit
// rien, c'est exactement la taille de l'angle mort — la même leçon que `VueTableaux.test.tsx` avait
// tirée en son temps, sur la feature voisine.
//
// On mocke les hooks de données : le sujet est l'**assemblage** (la vue se monte, distribue ce
// qu'elle a lu, et nomme ses états), pas le contenu servi par le réseau.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSessionSuivisStore } from '../../shared/stores/sessionSuivisStore'
import { useArchers } from '../archers/hooks'
import { useDeparts } from '../departs/hooks'
import { getPlanDeCibles } from '../placement/api'
import { useAffectations } from '../routage/hooks'
import { useTableauxDesDeparts } from '../tableaux/hooks'
import { useDeroule } from './deroule'
import { VueSuivi } from './VueSuivi'

vi.mock('../archers/hooks', () => ({ useArchers: vi.fn() }))
vi.mock('../clubs/hooks', () => ({ useClubs: () => ({ data: [], isError: false }) }))
vi.mock('../departs/hooks', () => ({ useDeparts: vi.fn() }))
vi.mock('../placement/api', () => ({ getPlanDeCibles: vi.fn() }))
vi.mock('../routage/hooks', () => ({ useAffectations: vi.fn() }))
vi.mock('../tableaux/hooks', () => ({ useTableauxDesDeparts: vi.fn() }))
vi.mock('./deroule', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./deroule')>()),
  useDeroule: vi.fn(),
}))

const DEPART = {
  id: 10,
  tournoi_id: 1,
  numero: 1,
  horaire: '09:00',
  tarif_centimes: 800,
  quota: null,
  etat: 'ouvert',
}

const ARCHER = { id: 7, prenom: 'Luc', nom: 'MARTIN', club_id: 2 }

const PLAN = {
  depart_id: 10,
  cibles: [
    {
      index: 3,
      capacite: 4,
      mixite_non_garantie: false,
      cloisonnement_non_respecte: false,
      placements: [{ position: 'B', archer_id: 7, blason_id: 1, inscription_id: 100 }],
    },
  ],
  conflits: [],
}

// Les retours de React Query comptent une trentaine de champs dont aucun n'intervient ici : double
// de test assumé (règle 4-front), comme dans `TableClassement.test.tsx`.
const resultat = (patch: Record<string, unknown>) => patch as never

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

describe('VueSuivi — montage', () => {
  beforeEach(() => {
    useSessionSuivisStore.setState(useSessionSuivisStore.getInitialState())
    vi.mocked(useArchers).mockReturnValue(
      resultat({ data: [ARCHER], isLoading: false, isSuccess: true, isError: false }),
    )
    vi.mocked(useDeparts).mockReturnValue(
      resultat({ data: [DEPART], isLoading: false, isError: false }),
    )
    vi.mocked(getPlanDeCibles).mockResolvedValue(resultat(PLAN))
    vi.mocked(useAffectations).mockReturnValue(resultat({ data: undefined, isError: false }))
    vi.mocked(useTableauxDesDeparts).mockReturnValue([])
    vi.mocked(useDeroule).mockReturnValue(resultat({ data: undefined, isError: false }))
  })

  it('se monte sans suivi et invite à chercher', () => {
    // Le cas d'entrée : aucun archer suivi, la recherche est la seule chose à faire.
    render(<Cadre enfants={<VueSuivi tournoiId={1} />} />)

    expect(screen.getByLabelText(/Rechercher un archer/)).toBeInTheDocument()
  })

  it('rend la carte d’un archer suivi, avec sa place', async () => {
    useSessionSuivisStore.setState({ suivis: [{ archerId: 7, tournoiId: 1 }] })

    render(<Cadre enfants={<VueSuivi tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByText(/MARTIN/)).toBeInTheDocument())
  })

  it('dit que les duels sont indisponibles plutôt que de les taire', async () => {
    // ⚠️ Le correctif de 3ᵉ passe. Une lecture d'arbres qui échoue faisait **disparaître** la
    // section « duels » sans un mot, les volées restant affichées — une amputation indétectable.
    // Le message ne promet **rien** sur la qualification : elle passe par le même réseau.
    useSessionSuivisStore.setState({ suivis: [{ archerId: 7, tournoiId: 1 }] })
    vi.mocked(useTableauxDesDeparts).mockReturnValue([resultat({ isError: true, data: undefined })])
    vi.mocked(useDeroule).mockReturnValue(
      resultat({
        data: {
          tournoi_id: 1,
          archer_id: 7,
          cumul: 28,
          volees: [
            {
              numero: 1,
              valeurs: ['10', '9', '9'],
              points: 28,
              statut: 'valide',
              horodatage: null,
            },
          ],
        },
        isError: false,
      }),
    )

    render(<Cadre enfants={<VueSuivi tournoiId={1} />} />)

    await waitFor(() =>
      expect(screen.getByText(/Duels momentanément indisponibles/)).toBeInTheDocument(),
    )
    expect(screen.queryByText(/La qualification reste à jour/)).toBeNull()
  })

  it('ne crie pas à l’erreur quand une donnée déjà lue est encore là', async () => {
    // Symétrique : ces requêtes se rafraîchissent toutes les 20 s et React Query **conserve** la
    // dernière donnée lue à l'échec d'un refetch d'arrière-plan. Sans ce test, le bandeau rouge
    // pouvait s'afficher au-dessus des duels qu'il déclare indisponibles.
    useSessionSuivisStore.setState({ suivis: [{ archerId: 7, tournoiId: 1 }] })
    vi.mocked(useTableauxDesDeparts).mockReturnValue([
      resultat({ isError: true, data: { depart_id: 10, tableaux: [] } }),
    ])

    render(<Cadre enfants={<VueSuivi tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByText(/MARTIN/)).toBeInTheDocument())
    expect(screen.queryByText(/Duels momentanément indisponibles/)).toBeNull()
  })
})
