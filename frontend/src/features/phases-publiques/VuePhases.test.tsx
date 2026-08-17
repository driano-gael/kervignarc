// Tests de **montage** de l'onglet public « Rencontres » (E05US031).
//
// Ce fichier existe pour la raison qu'`E07US005` a payée cher : *une feature front sans un seul
// rendu testé a un angle mort de cette taille*. Les tests de logique pure de `presentation.test.ts`
// et de `shared/rencontres/modele.test.ts` n'appellent jamais React — ils ne peuvent donc rien voir
// du **routage par type**, qui est pourtant le cœur de cette US : c'est lui qui décide qu'une phase
// de poules n'est pas rendue comme un arbre, et le tromper produit un écran plausible et faux.
//
// Deux comportements y sont verrouillés, et aucun des deux n'est visible depuis le code :
//  1. chaque type de phase atteint **sa** vue ;
//  2. un type sans vue détaillée **dit où regarder** au lieu de laisser un blanc.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Depart } from '../departs/api'
import { getDeparts } from '../departs/api'
import { getEtatPoules } from '../poules/api'
import { getEtatSuisse } from '../suisse/api'
import { getEtatBigShootOffPublic } from '../big-shoot-off/api'
import { getTableaux } from '../tableaux/api'
import type { PhasePublique } from './api'
import { getPhasesPubliques } from './api'
import { VuePhases } from './VuePhases'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getPhasesPubliques: vi.fn(),
}))
vi.mock('../departs/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/api')>()),
  getDeparts: vi.fn(),
}))
vi.mock('../poules/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../poules/api')>()),
  getEtatPoules: vi.fn(),
}))
vi.mock('../suisse/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../suisse/api')>()),
  getEtatSuisse: vi.fn(),
}))
vi.mock('../big-shoot-off/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../big-shoot-off/api')>()),
  getEtatBigShootOffPublic: vi.fn(),
}))
vi.mock('../tableaux/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../tableaux/api')>()),
  getTableaux: vi.fn(),
}))

const CRENEAU: Depart = {
  id: 41,
  tournoi_id: 1,
  numero: 1,
  horaire: '09:00',
  tarif_centimes: 800,
  quota: null,
  etat: 'ouvert',
}

const MARTIN = { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' }
const DURAND = { archer_id: 2, nom: 'DURAND', prenom: 'Eve' }

const phase = (type: string, id = 10): PhasePublique => ({ id, ordre: 2, type, statut: 'en_cours' })

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

describe('VuePhases — routage par type', () => {
  beforeEach(() => {
    vi.mocked(getDeparts).mockResolvedValue([CRENEAU])
    vi.mocked(getEtatPoules).mockResolvedValue({
      phase_id: 10,
      repartition: { effectif: 2, taille_visee: 2, nb_poules: 1, tailles: [2] },
      poules: [
        {
          numero: 1,
          membres: [MARTIN, DURAND],
          bloc: null,
          rencontres: [
            {
              numero: 1,
              poule: 1,
              tour: 1,
              couloirs: null,
              haut: MARTIN,
              bas: DURAND,
              points_haut: null,
              points_bas: null,
              vainqueur: null,
              termine: false,
              validee: false,
              desynchronisee: false,
            },
          ],
          classement: [],
          qualifies: [],
          barrage_requis: false,
        },
      ],
      conflits: [],
    })
    vi.mocked(getEtatSuisse).mockResolvedValue({
      phase_id: 10,
      nb_rondes: 2,
      rondes_maximales: 2,
      effectif: 2,
      rondes: [{ numero: 1, rencontres: [], bye: MARTIN, close: false }],
      classement: [],
      conflits: [],
    })
    vi.mocked(getEtatBigShootOffPublic).mockResolvedValue({
      phase_id: 10,
      projection: {
        effectif: 2,
        eliminations: [1],
        paliers: [1],
        restants: 2,
        manches_jouables: 1,
      },
      tireurs: [{ ...MARTIN, en_lice: true, rang: null, scores: [] }],
      manches: [],
      termine: false,
      barrage: null,
    })
    vi.mocked(getTableaux).mockResolvedValue({ depart_id: 41, tableaux: [] })
  })

  it('rend une phase de poules par la vue commune des rencontres', async () => {
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('poules')])

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    expect(await screen.findByText('Poule 1')).toBeInTheDocument()
    expect(screen.getByText('Tour 1')).toBeInTheDocument()
    expect(screen.getByText('Luc MARTIN')).toBeInTheDocument()
  })

  it('rend un système suisse par la même vue, en nommant l’exempt', async () => {
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('suisse')])

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    expect(await screen.findByText('Ronde 1')).toBeInTheDocument()
    // Le bye se **dit** : un archer absent de tous les appariements, sans un mot, se lit comme un
    // oubli alors qu'il marque comme s'il avait gagné.
    expect(screen.getByText('Exempt : Luc MARTIN')).toBeInTheDocument()
  })

  it('rend un Big Shoot Off par sa vue propre', async () => {
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('big_shoot_off')])

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    // L'échelle du format — « 2 → 1 » —, qui n'existe dans aucune autre vue.
    expect(await screen.findByText('2 archers en lice')).toBeInTheDocument()
    expect(screen.getByText('En lice')).toBeInTheDocument()
  })

  it('renvoie la qualification vers l’onglet où elle se lit, au lieu d’un blanc', async () => {
    // ⚠️ C'est la règle d'ADR-0064 appliquée : *un écran de salle n'a personne devant lui pour
    // comprendre ce qui manque*. Une phase sans vue détaillée doit donc **orienter**, pas se taire.
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('qualification')])

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    expect(await screen.findByText(/onglet « Classement »/)).toBeInTheDocument()
  })

  it('dit sans rien promettre pour un type qu’il ne sait pas rendre', async () => {
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('colline')])

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    expect(await screen.findByText(/n’est pas encore consultable/)).toBeInTheDocument()
  })
})

describe('VuePhases — « mes archers »', () => {
  beforeEach(() => {
    vi.mocked(getDeparts).mockResolvedValue([CRENEAU])
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('poules')])
    vi.mocked(getEtatPoules).mockResolvedValue({
      phase_id: 10,
      repartition: { effectif: 2, taille_visee: 2, nb_poules: 1, tailles: [2] },
      poules: [
        {
          numero: 1,
          membres: [MARTIN, DURAND],
          bloc: null,
          rencontres: [],
          classement: [
            {
              rang: 1,
              archer_id: MARTIN.archer_id,
              points_match: 2,
              diff_sets: 1,
              diff_score: 4,
              nb_dix: 1,
              nb_neuf: 0,
              ex_aequo: false,
            },
          ],
          qualifies: [],
          barrage_requis: false,
        },
      ],
      conflits: [],
    })
  })

  it('centre sur un archer suivi, avec son rang', async () => {
    render(
      <Cadre enfants={<VuePhases tournoiId={1} mode="suivis" suivis={[MARTIN.archer_id]} />} />,
    )

    expect(await screen.findByText('Luc MARTIN')).toBeInTheDocument()
    // Dans un format sans arbre, **le rang est la position** : le taire livrerait une liste de
    // résultats sans jamais dire où en est l'archer.
    expect(screen.getByText(/Poule 1 ·/)).toBeInTheDocument()
  })

  it('distingue « aucun de vos archers ici » de « rien à afficher »', async () => {
    // Le cas banal : on suit des archers d'une catégorie, on regarde la poule d'une autre. C'est
    // celui qu'E16US004 avait manqué sur l'arbre — on ne le refait pas ici.
    render(<Cadre enfants={<VuePhases tournoiId={1} mode="suivis" suivis={[999]} />} />)

    await waitFor(() =>
      expect(screen.getByText(/Aucun des archers que vous suivez/)).toBeInTheDocument(),
    )
  })

  it('n’honore pas « mes archers » sur l’écran de salle', async () => {
    // `interactif={false}` : personne ne suit d'archer devant un projecteur. La lecture y est
    // **toujours** complète (CA E07US004), même si un mode traîne dans les props.
    render(
      <Cadre
        enfants={<VuePhases tournoiId={1} interactif={false} mode="suivis" suivis={[999]} />}
      />,
    )

    expect(await screen.findByText('Poule 1')).toBeInTheDocument()
    expect(screen.queryByText(/Aucun des archers que vous suivez/)).not.toBeInTheDocument()
  })
})
