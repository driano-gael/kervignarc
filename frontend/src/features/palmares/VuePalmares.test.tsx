// Tests de **montage** du palmarès (E06US004, centrage ajouté par E16US004).
//
// Un seul invariant, celui qui n'a pas de recours s'il tombe : **le centrage « mes archers » ne
// touche jamais les podiums**. C'est un garde-fou qui *interdit* un comportement, donc la sorte de
// règle qu'un refactor casse en silence — la revue d'E16US004 l'a relevée énoncée en docstring et
// appliquée dans le JSX, sans un test. Un podium amputé de ses médaillés ne répond plus à « qui a
// gagné », et le spectateur qui ne suit aucun médaillé est celui pour qui la question se pose.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { LignePalmares, Palmares } from './api'
import { getPalmares } from './api'
import { VuePalmares } from './VuePalmares'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getPalmares: vi.fn(),
}))

// Les catégories alimentent le filtre de l'appli publique ; sans elles la vue monte quand même.
vi.mock('../categories/hooks', () => ({ useCategories: () => ({ data: [] }) }))

function ligne(patch: Partial<LignePalmares> = {}): LignePalmares {
  return {
    rang_min: 1,
    rang_max: 1,
    rang_categorie_min: 1,
    rang_categorie_max: 1,
    archer_id: 1,
    nom: 'CHAMPION',
    prenom: 'Ada',
    categorie_id: 3,
    categorie_libelle: 'Senior 1 Homme',
    club_id: 2,
    origine: 'duels',
    statut: 'en_lice',
    decerne: true,
    en_lice: false,
    ...patch,
  }
}

// Le médaillé n'est **pas** suivi ; l'archer suivi est loin derrière. C'est le cas qui compte.
const MEDAILLE = ligne()
const MON_ARCHER = ligne({
  archer_id: 99,
  nom: 'MARTIN',
  prenom: 'Luc',
  rang_min: 17,
  rang_max: 17,
  rang_categorie_min: 9,
  rang_categorie_max: 9,
  decerne: false,
})

const CLUB = {
  rang: 1,
  club_id: 2,
  club_libelle: 'Compagnie de Kervignarc',
  medailles_or: 1,
  medailles_argent: 0,
  medailles_bronze: 0,
}

const PALMARES: Palmares = {
  tournoi_id: 1,
  podiums: [
    {
      portee: 'categorie',
      cle: 3,
      libelle: 'Senior 1 Homme',
      effectif: 2,
      en_attente: false,
      places: [{ rang: 1, ligne: MEDAILLE }],
    },
  ],
  classement_clubs: {
    lignes: [
      {
        rang: 1,
        club_id: 2,
        club_libelle: 'Compagnie de Kervignarc',
        medailles_or: 1,
        medailles_argent: 0,
        medailles_bronze: 0,
      },
    ],
    portees_comptees: ['categorie'],
    portees_reglees: ['categorie'],
    provisoire: false,
  },
  profondeur_podium: 4,
  classement_vide: false,
  lignes: [MEDAILLE, MON_ARCHER],
}

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

describe('VuePalmares — centrage « mes archers »', () => {
  beforeEach(() => {
    vi.mocked(getPalmares).mockResolvedValue(PALMARES)
  })

  it('garde le podium entier alors qu’aucun médaillé n’est suivi', async () => {
    render(<Cadre enfants={<VuePalmares tournoiId={1} mode="suivis" suivis={[99]} />} />)

    // Le médaillé est là, bien qu'on ne le suive pas : le podium dit qui a gagné, pas qui l'on suit.
    await waitFor(() => expect(screen.getByText(/CHAMPION/)).toBeInTheDocument())
    expect(screen.getByLabelText('Podium Senior 1 Homme')).toBeInTheDocument()
  })

  it('centre en revanche le classement final sur les archers suivis', async () => {
    // Le symétrique : sans lui, le test précédent passerait avec un composant qui ne centre rien.
    render(<Cadre enfants={<VuePalmares tournoiId={1} mode="suivis" suivis={[99]} />} />)

    await waitFor(() => expect(screen.getByText('Mes archers')).toBeInTheDocument())
    // Nommé, et non pris par sa position : E16US017 a ajouté un second tableau à cet écran (le
    // classement des clubs), et `getByRole('table')` seul est devenu ambigu.
    const classement = within(screen.getByLabelText('Mes archers')).getByRole('table')
    expect(classement).toHaveTextContent('MARTIN')
    expect(classement).not.toHaveTextContent('CHAMPION')
  })

  it('nomme le vide du filtre sans imputer la cause au seul interrupteur', async () => {
    // Arbitrage (d) : « aucun de vos archers ici » n'est pas « aucun archer classé ». Le message ne
    // désigne pas le créneau ni la catégorie, parce que l'un et l'autre peuvent être en cause.
    render(<Cadre enfants={<VuePalmares tournoiId={1} mode="suivis" suivis={[404]} />} />)

    await waitFor(() =>
      expect(screen.getByText(/Aucun des archers que vous suivez/)).toBeInTheDocument(),
    )
    // ⚠️ Assertion sur « élargissez le filtre » (2ᵉ passe de revue) : sans elle, le test passait
    // **aussi** avec l'ancien message, qui n'imputait la cause qu'à l'interrupteur — il ne prouvait
    // donc rien du correctif qu'il prétend nommer. Cet écran porte un filtre par catégorie qui vide
    // la liste tout aussi souvent.
    expect(screen.getByText(/élargissez le filtre/)).toBeInTheDocument()
    expect(screen.queryByText(/Aucun archer classé/)).toBeNull()
    // Et le podium, lui, reste affiché : ce vide-là ne l'ampute pas non plus.
    expect(screen.getByText(/CHAMPION/)).toBeInTheDocument()
  })
})

describe('VuePalmares — un filtre qui vide le classement ne retire pas les podiums', () => {
  it('garde les podiums quand la sélection ne contient aucun archer', async () => {
    // Le bloquant de la 3ᵉ passe, côté écran : la garde « aucun archer classé » portait sur les
    // lignes, qui sont filtrées, et emportait tous les podiums avec elle. Un podium est celui du
    // tournoi — sa présence prouve justement que le tournoi est classé.
    vi.mocked(getPalmares).mockResolvedValue({ ...PALMARES, lignes: [] })
    render(<Cadre enfants={<VuePalmares tournoiId={1} />} />)

    expect(await screen.findByText('Senior 1 Homme')).toBeInTheDocument()
    expect(screen.queryByText(/Aucun archer classé pour l['’]instant/)).not.toBeInTheDocument()
  })

  it('ne dit pas « aucun archer classé » quand AUCUNE portée n’est cochée', async () => {
    // Le 4ᵉ déplacement : `podiums` vide est un réglage **valide** (CA « n'en cocher aucune »), et
    // `lignes` vide peut venir du filtre. Les deux réunis, la garde précédente concluait « rien
    // n'est classé » sur un tournoi entièrement classé. Le serveur porte désormais le fait.
    vi.mocked(getPalmares).mockResolvedValue({
      ...PALMARES,
      podiums: [],
      lignes: [],
      classement_vide: false,
    })
    render(<Cadre enfants={<VuePalmares tournoiId={1} />} />)

    expect(await screen.findByText(/Aucun archer dans cette sélection/)).toBeInTheDocument()
    expect(screen.queryByText(/Aucun archer classé pour l['’]instant/)).not.toBeInTheDocument()
  })

  it('dit « aucun archer classé » quand le tournoi ne l’est vraiment pas', async () => {
    vi.mocked(getPalmares).mockResolvedValue({
      ...PALMARES,
      podiums: [],
      lignes: [],
      classement_vide: true,
    })
    render(<Cadre enfants={<VuePalmares tournoiId={1} />} />)

    expect(await screen.findByText(/Aucun archer classé pour l['’]instant/)).toBeInTheDocument()
  })
})

describe('VuePalmares — classement des clubs (E16US017)', () => {
  it('affiche le décompte de médailles à côté des podiums', async () => {
    vi.mocked(getPalmares).mockResolvedValue(PALMARES)
    render(<Cadre enfants={<VuePalmares tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByLabelText('Classement des clubs')).toBeInTheDocument())
    expect(
      within(screen.getByLabelText('Classement des clubs')).getByRole('table'),
    ).toHaveTextContent('Compagnie de Kervignarc')
  })

  it('rend les rangs du serveur, sauts d’ex æquo compris', async () => {
    // ⚠️ Le garde-fou qui n'a pas de recours : deux clubs à décompte identique partagent le rang 1
    // et le suivant est **3ᵉ**. Numéroter sur l'index de la boucle rendrait 1-2-3 — un classement
    // cohérent et faux, exactement ce que `DETTE-029` décrit.
    vi.mocked(getPalmares).mockResolvedValue({
      ...PALMARES,
      classement_clubs: {
        ...PALMARES.classement_clubs,
        lignes: [
          { ...CLUB, rang: 1, club_id: 1, club_libelle: 'Arc Club de Vannes' },
          { ...CLUB, rang: 1, club_id: 2, club_libelle: 'Compagnie de Kervignarc' },
          { ...CLUB, rang: 3, club_id: 3, club_libelle: 'Les Archers du Golfe', medailles_or: 0 },
        ],
      },
    })
    render(<Cadre enfants={<VuePalmares tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByLabelText('Classement des clubs')).toBeInTheDocument())
    const rangs = within(screen.getByLabelText('Classement des clubs'))
      .getAllByRole('row')
      .slice(1)
      .map((ligne) => ligne.querySelectorAll('td')[0]?.textContent)
    expect(rangs).toEqual(['1ᵉʳ', '1ᵉʳ', '3ᵉ'])
  })

  it('dit pourquoi il n’y a rien plutôt que de laisser un blanc', async () => {
    // Arbitrage du 04/09/2026 : réglé sur la seule portée *club*, le décompte n'a aucune base. Un
    // tableau vide se lirait comme une panne, et l'organisateur irait chercher au mauvais endroit.
    vi.mocked(getPalmares).mockResolvedValue({
      ...PALMARES,
      classement_clubs: {
        lignes: [],
        portees_comptees: [],
        portees_reglees: ['club'],
        provisoire: false,
      },
    })
    render(<Cadre enfants={<VuePalmares tournoiId={1} />} />)

    await waitFor(() =>
      expect(screen.getByText(/à l’intérieur de chaque club/)).toBeInTheDocument(),
    )
    expect(within(screen.getByLabelText('Classement des clubs')).queryByRole('table')).toBeNull()
  })
})

describe('VuePalmares — classement des clubs, correctifs de revue', () => {
  it('range chaque métal dans sa propre colonne', async () => {
    // ⚠️ Relevé en revue (axe B) : aucune surface n'ancrait *quelle colonne porte quel métal*, si
    // bien qu'une permutation argent ↔ bronze restait verte partout. Trois valeurs distinctes.
    vi.mocked(getPalmares).mockResolvedValue({
      ...PALMARES,
      classement_clubs: {
        ...PALMARES.classement_clubs,
        lignes: [{ ...CLUB, medailles_or: 3, medailles_argent: 2, medailles_bronze: 1 }],
      },
    })
    render(<Cadre enfants={<VuePalmares tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByLabelText('Classement des clubs')).toBeInTheDocument())
    const ligne = within(screen.getByLabelText('Classement des clubs')).getAllByRole('row')[1]
    expect([...(ligne?.querySelectorAll('td') ?? [])].map((c) => c.textContent)).toEqual([
      '1ᵉʳ',
      'Compagnie de Kervignarc',
      '3',
      '2',
      '1',
    ])
  })

  it('n’affiche rien du tout quand le tournoi ne récompense rien', async () => {
    // ⚠️ Relevé en revue (axe C2) : la garde vivait en JSX et lisait `podiums` — 5ᵉ inférence du
    // même genre sur ce DTO. Le fait est désormais servi (`portees_reglees`), donc testable ici.
    vi.mocked(getPalmares).mockResolvedValue({
      ...PALMARES,
      podiums: [],
      classement_clubs: {
        lignes: [],
        portees_comptees: [],
        portees_reglees: [],
        provisoire: false,
      },
    })
    render(<Cadre enfants={<VuePalmares tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByText('Classement complet')).toBeInTheDocument())
    expect(screen.queryByLabelText('Classement des clubs')).toBeNull()
  })

  it('dit qu’aucun club n’a de médaille plutôt que de les ranger tous 1ᵉʳˢ', async () => {
    // ⚠️ Relevé en revue (axe C1) : le domaine rendait un club par ligne à (0,0,0), donc tous au
    // rang 1 — « un classement où tout le monde est premier », que le CA interdit. Le serveur ne
    // renvoie plus de lignes ; l'écran doit dire pourquoi.
    vi.mocked(getPalmares).mockResolvedValue({
      ...PALMARES,
      classement_clubs: { ...PALMARES.classement_clubs, lignes: [], provisoire: true },
    })
    render(<Cadre enfants={<VuePalmares tournoiId={1} />} />)

    await waitFor(() =>
      expect(screen.getByText('Aucun club n’a encore de médaille.')).toBeInTheDocument(),
    )
    expect(within(screen.getByLabelText('Classement des clubs')).queryByRole('table')).toBeNull()
  })
})
