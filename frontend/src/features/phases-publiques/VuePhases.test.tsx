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
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Depart } from '../departs/api'
import { getDeparts } from '../departs/api'
import { getEtatPoules } from '../poules/api'
import { getEtatSuisse } from '../suisse/api'
import { getEtatBigShootOffPublic } from '../big-shoot-off/api'
import { getTableaux, type TableauPublic } from '../tableaux/api'
import type { Place } from '../../shared/salle/place'
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

const mkTableau = (over: Partial<TableauPublic> = {}): TableauPublic => ({
  phase_id: 10,
  ordre: 2,
  type: 'elimination_directe',
  effectif: 8,
  taille: 8,
  nb_tours: 3,
  est_termine: false,
  duels: [],
  podium: [],
  en_attente_de: null,
  ...over,
})

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
              // ⚠️ **À cheval sur deux cibles, délibérément.** Le défaut d'origine était dans le
              // JSX — il ne lisait que la première place —, donc `libelleCibles` testé seul ne le
              // couvre pas : il faut qu'un rendu **traverse** le composant avec deux cibles
              // distinctes (relevé à la 2ᵉ passe de revue).
              couloirs: [
                [1, 'C'],
                [2, 'A'],
              ] as [Place, Place],
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
    // ⚠️ **Fixture cohérente avec ce que le serveur produit réellement.** La première rédaction
    // posait `paliers: [1]` **et** `restants: 2` — impossible, `restants` valant `paliers[-1]` —
    // puis assertait « 2 archers en lice » sur cette valeur. Le test consacrait ainsi le défaut
    // qu'il aurait dû trouver : `restants` est l'effectif de **fin** de format, pas le compte des
    // archers qui tirent encore.
    vi.mocked(getEtatBigShootOffPublic).mockResolvedValue({
      phase_id: 10,
      projection: {
        effectif: 2,
        paliers: [1],
        restants: 1,
      },
      tireurs: [
        { ...MARTIN, rang: null, scores: [] },
        { ...DURAND, rang: null, scores: [] },
      ],
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
    // Les DEUX cibles sont nommées : « Cible 1C/A » enverrait le second archer au mauvais endroit.
    expect(screen.getByText('Cibles 1C et 2A')).toBeInTheDocument()
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

    // L'échelle du format — « 2 → 1 » —, qui n'existe dans aucune autre vue. Le compte annoncé est
    // celui des archers qui **tirent encore** (deux), pas l'effectif de fin (`restants`, qui vaut 1
    // ici) : c'est tout l'objet du correctif.
    expect(await screen.findByText('2 archers en lice')).toBeInTheDocument()
    expect(screen.getAllByText('En lice')).toHaveLength(2)
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

  // ⚠️ **Le sélecteur n'était monté par AUCUN test.** Les six cas ci-dessus fournissent tous une
  // liste d'**une seule** phase, donc `phases.data.length > 1` était toujours faux : le CA reversé
  // au cadrage — « le classement d'une phase terminée reste consultable » — était couvert par des
  // tests qui n'atteignaient jamais la surface qui le rend vrai.
  it('laisse consulter une phase terminée après le démarrage de la suivante', async () => {
    vi.mocked(getPhasesPubliques).mockResolvedValue([
      { id: 9, ordre: 1, type: 'poules', statut: 'terminee' },
      { id: 10, ordre: 2, type: 'suisse', statut: 'en_cours' },
    ])

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    // Par défaut, ce qui se joue : le suisse.
    expect(await screen.findByText('Ronde 1')).toBeInTheDocument()

    // Les poules terminées restent dans la liste, avec leur rang et leur statut.
    const selecteur = screen.getByRole('combobox')
    expect(screen.getByRole('option', { name: '1. Poules — terminée' })).toBeInTheDocument()

    await userEvent.selectOptions(selecteur, '9')
    expect(await screen.findByText('Poule 1')).toBeInTheDocument()
  })

  it('cache le sélecteur sur l’écran de salle, où personne ne peut choisir', async () => {
    vi.mocked(getPhasesPubliques).mockResolvedValue([
      { id: 9, ordre: 1, type: 'poules', statut: 'terminee' },
      { id: 10, ordre: 2, type: 'suisse', statut: 'en_cours' },
    ])

    render(<Cadre enfants={<VuePhases tournoiId={1} interactif={false} />} />)

    expect(await screen.findByText('Ronde 1')).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  // ⚠️ **Le point de non-régression que la fiche de recette désigne elle-même** (scénario 8) :
  // l'arbre n'a pas bougé. `VueTableaux` gagne pourtant une prop `phaseId` et une chaîne de
  // sélection à trois branches, qu'aucun test ne montait.
  it('impose la phase choisie à l’arbre, sans lui laisser un second sélecteur', async () => {
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('elimination_directe', 10)])
    vi.mocked(getTableaux).mockResolvedValue({
      depart_id: 41,
      tableaux: [mkTableau({ phase_id: 10 })],
    })

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    expect(await screen.findByText(/8 archers/)).toBeInTheDocument()
    // Un seul sélecteur au plus sur l'écran — celui de `VuePhases`, masqué ici (une seule phase).
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  // ⚠️ **Une seule marque « en cours », sur le premier tour ouvert.** Le suisse n'apparie la ronde
  // N+1 qu'après la N, donc un seul tour ouvert y existe — mais les poules dérivent le round-robin
  // **complet** dès la composition. Sans cet arbitrage, une poule de 4 affichait « Tour 1 en cours ·
  // Tour 2 en cours · Tour 3 en cours », et la marque perdait ce qu'elle sert à dire : distinguer le
  // tour qu'on regarde tirer de ceux qui sont derrière.
  it('ne marque « en cours » que le premier tour non clos d’une poule', async () => {
    const rencontre = (numero: number, tour: number, validee: boolean) => ({
      numero,
      poule: 1,
      tour,
      couloirs: null,
      haut: MARTIN,
      bas: DURAND,
      points_haut: null,
      points_bas: null,
      vainqueur: null,
      termine: validee,
      validee,
      desynchronisee: false,
    })
    vi.mocked(getEtatPoules).mockResolvedValue({
      phase_id: 10,
      repartition: { effectif: 2, taille_visee: 2, nb_poules: 1, tailles: [2] },
      poules: [
        {
          numero: 1,
          membres: [MARTIN, DURAND],
          bloc: null,
          // Tour 1 scellé, tours 2 et 3 encore à tirer : le round-robin complet existe dès la
          // composition, tel que le serveur le rend.
          rencontres: [rencontre(1, 1, true), rencontre(2, 2, false), rencontre(3, 3, false)],
          classement: [],
          qualifies: [],
          barrage_requis: false,
        },
      ],
      conflits: [],
    })
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('poules')])

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    expect(await screen.findByText('Tour 3')).toBeInTheDocument()
    expect(screen.getAllByText('en cours')).toHaveLength(1)
  })

  // ⚠️ **Le correctif le plus facile à réintroduire en silence** : il tient à un `instanceof` et à
  // une liste de statuts. Sans ces deux cas, revenir au booléen `isError` ne ferait rougir personne
  // — et l'écran affirmerait « pas encore prête » pendant qu'une phase se joue.
  it('dit qu’une phase non réglée n’est pas prête — c’est un état, pas une panne', async () => {
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('suisse')])
    vi.mocked(getEtatSuisse).mockRejectedValue(
      new ErreurApi(409, 'phase_non_reglee', 'La phase n’est pas réglée.'),
    )

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    expect(await screen.findByText(/pas encore prête à être suivie/)).toBeInTheDocument()
  })

  it('ne confond pas une coupure réseau avec un refus du serveur', async () => {
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('suisse')])
    vi.mocked(getEtatSuisse).mockRejectedValue(new TypeError('Failed to fetch'))

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    expect(await screen.findByText(/Connexion momentanément perdue/)).toBeInTheDocument()
    expect(screen.queryByText(/pas encore prête à être suivie/)).not.toBeInTheDocument()
  })

  it('dit que l’arbre de cette phase n’est pas monté, plutôt que d’en montrer un autre', async () => {
    vi.mocked(getPhasesPubliques).mockResolvedValue([phase('elimination_directe', 10)])
    vi.mocked(getTableaux).mockResolvedValue({
      depart_id: 41,
      tableaux: [mkTableau({ phase_id: 777 })],
    })

    render(<Cadre enfants={<VuePhases tournoiId={1} />} />)

    expect(await screen.findByText(/n’est pas encore monté/)).toBeInTheDocument()
    // L'arbre de l'AUTRE phase ne doit pas s'afficher en remplacement.
    expect(screen.queryByText(/8 archers/)).not.toBeInTheDocument()
  })
})
