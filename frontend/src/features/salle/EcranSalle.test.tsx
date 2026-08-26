// Tests de **montage** de l'écran de salle — le point de montage de l'annonce de pause.
//
// ⚠️ **Ce fichier existe à cause d'un bloquant de revue (E05US034, axes C2 et adversarial).** Le
// bandeau de pause vivait dans `VueEnCours`, et `EN_COURS` **n'est pas** au déroulé par défaut
// (`SequenceVues.par_defaut` côté domaine : classement, plan de cibles, suivi). Sur un écran
// branché sans configuration — le cas nominal — l'annonce ne s'affichait donc jamais, alors que
// quatre documents du dépôt affirmaient le contraire.
//
// Le défaut n'était **pas** dans une fonction : `resumeDeRelance` et `peutPoserUnePause` étaient
// justes, et tous les tests verts. Il était dans le **point de montage** — la seule chose qu'un
// test de logique pure ne peut pas voir. D'où un test qui monte réellement le composant et regarde
// ce qui s'affiche pendant qu'une **autre** vue tourne.
//
// Les vues sont des témoins : leur rendu a ses propres tests, ce qu'on épingle ici est ce qui les
// coiffe.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Depart } from '../departs/api'
import { getDeparts } from '../departs/api'
import type { Phase } from '../phases/api'
import { getAvancement } from '../phases/api'
import type { Identite } from '../identite/api'
import { getIdentite } from '../identite/api'
import { EcranSalle } from './EcranSalle'

vi.mock('../departs/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/api')>()),
  getDeparts: vi.fn(),
}))
vi.mock('../phases/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../phases/api')>()),
  getAvancement: vi.fn(),
}))
// Le déroulé de l'écran : on impose une rotation qui ne passe **jamais** par `en_cours`, c'est-à-dire
// exactement le déroulé par défaut d'un écran neuf.
vi.mock('../ecrans/hooks', () => ({
  useAffichageEcran: () => ({
    data: {
      sous_controle: false,
      vue_figee: null,
      vues: [{ vue: 'classement', cadence_s: 30 }],
      deroule_repli: [{ vue: 'classement', cadence_s: 30 }],
      reste_s: null,
    },
    dataUpdatedAt: 0,
    isError: false,
  }),
}))
// Témoins : ces vues font leurs propres requêtes, hors sujet ici.
vi.mock('../competition/VueClassement', () => ({
  VueClassement: () => <div data-testid="classement" />,
}))
vi.mock('../placement/PlanCiblesPublic', () => ({
  PlanCiblesDeSalle: () => <div data-testid="plan-cibles" />,
}))
vi.mock('../palmares/VuePalmares', () => ({ VuePalmares: () => <div data-testid="palmares" /> }))
vi.mock('../routage/VueAffectations', () => ({
  VueAffectations: () => <div data-testid="affectations" />,
}))
vi.mock('../en-cours/VueEnCours', () => ({ VueEnCours: () => <div data-testid="en-cours" /> }))
vi.mock('../suivi-deroule/hooks', () => ({ useSuiviDeroule: () => ({ data: undefined }) }))
// E16US006 : l'identité est une vraie requête, on la sert depuis une doublure typée plutôt que
// de neutraliser `HabillageIdentite` — c'est **son montage** que les tests plus bas vérifient.
vi.mock('../identite/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../identite/api')>()),
  getIdentite: vi.fn(),
}))

// ⚠️ **Décor typé sans `as unknown as`** (correctif de revue, axe B). La première rédaction cassait
// le type, et la fixture était objectivement fausse : sans `etat`, `departDeSalle` tombait dans son
// **dernier recours** (« le dernier de la liste ») au lieu du chemin nominal `etat === 'lance'` — le
// test empruntait donc une branche dégradée sans le dire. `etat: 'lance'` est ce que l'écran voit
// un jour de tournoi.
const CRENEAU: Depart = {
  id: 3,
  tournoi_id: 1,
  numero: 1,
  horaire: '09:00',
  tarif_centimes: 800,
  quota: null,
  etat: 'lance',
}

function phase(patch: Partial<Phase> & Pick<Phase, 'id' | 'ordre' | 'type' | 'statut'>): Phase {
  return {
    depart_id: 3,
    sources: [],
    effectif: 16,
    barrage_jusqu_au: null,
    profondeur: null,
    poules: null,
    big_shoot_off: null,
    suisse: null,
    colline: null,
    decoupage: null,
    ...patch,
  }
}

function monter(noeud: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{noeud}</QueryClientProvider>)
}

beforeEach(() => {
  vi.mocked(getDeparts).mockResolvedValue([CRENEAU])
  vi.mocked(getAvancement).mockReset()
})

describe('EcranSalle — l’annonce de pause est hors rotation (CA E05US034)', () => {
  it('annonce la pause alors que la vue en rotation n’est pas « en cours »', async () => {
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 8, ordre: 1, type: 'suisse', statut: 'en_pause' }),
    ])

    monter(<EcranSalle libelle="Gymnase" tournoiId={1} />)

    // Le témoin prouve qu'on est bien sur une **autre** vue : sans cette assertion, le test
    // passerait aussi si la rotation était tombée sur `en_cours`, c'est-à-dire sans rien prouver.
    expect(await screen.findByTestId('classement')).toBeInTheDocument()
    expect(await screen.findByText(/le tir est suspendu par l’organisation/i)).toBeInTheDocument()
  })

  it('n’annonce rien quand la salle tire', async () => {
    // Cas adverse : une annonce inconditionnelle afficherait « Pause » toute la journée sur un
    // écran projeté, ce qui est pire que le défaut qu'on vient de corriger.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 8, ordre: 1, type: 'suisse', statut: 'en_cours' }),
    ])

    monter(<EcranSalle libelle="Gymnase" tournoiId={1} />)

    expect(await screen.findByTestId('classement')).toBeInTheDocument()
    expect(screen.queryByText(/le tir est suspendu par l’organisation/i)).toBeNull()
  })

  it('nomme la phase suspendue au lieu d’annoncer une suspension générale', async () => {
    // ⚠️ **Le cas du bloquant de 2ᵉ passe** (axe B). La portée par défaut d'un arrêt est *la phase
    // seule*, et rien n'interdit deux phases en cours en parallèle. Le premier correctif testait
    // « au moins une phase en pause » : l'écran projeté annonçait au gymnase entier « le tir est
    // suspendu » pendant que le tableau tirait. Les deux cas ci-dessus ne pouvaient pas le voir —
    // à une seule phase, « une phase est en pause » et « la salle est arrêtée » sont la même chose.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 8, ordre: 1, type: 'suisse', statut: 'en_pause' }),
      phase({ id: 9, ordre: 2, type: 'elimination_directe', statut: 'en_cours' }),
    ])

    monter(<EcranSalle libelle="Gymnase" tournoiId={1} />)

    expect(
      await screen.findByText(/le tir est suspendu par l’organisation pour/i),
    ).toHaveTextContent(/système suisse/i)
  })
})

describe('EcranSalle — l’identité du tournoi habille la surface (CA E16US006, D-27)', () => {
  // ⚠️ **Tests de PLACEMENT, pas de rendu de composant.** `DETTE-085` a établi le prix de la
  // confusion : `E16US005` a livré un écran qui calculait ses repères et ne les rendait jamais, sans
  // qu'aucun test ne bouge, parce qu'aucun ne montait cet écran. Monter `HabillageIdentite` seul
  // prouverait qu'il sait poser des jetons ; il ne prouverait pas qu'`EcranSalle` l'appelle. Ces
  // deux tests-ci tombent si on retire l'habillage ou les logos du bandeau.

  it('pose les jetons de marque du tournoi sur la scène', async () => {
    vi.mocked(getAvancement).mockResolvedValue([])
    vi.mocked(getIdentite).mockResolvedValue(identiteDeTest())

    const { container } = monter(<EcranSalle libelle="Gymnase" tournoiId={1} />)

    await waitFor(() =>
      expect(container.querySelector('style')?.textContent).toContain('--brand-surface:#0b6e9e'),
    )
    expect(container.querySelector('[data-identite="identite-1"]')).not.toBeNull()
  })

  it('affiche les DEUX logos déposés dans le bandeau', async () => {
    // P07, question 2 : *« je n'ai pas vu le logo sur la maquette »*. Les deux marques du club —
    // l'édition et le club — sur la surface où l'on est le plus loin de l'écran.
    vi.mocked(getAvancement).mockResolvedValue([])
    vi.mocked(getIdentite).mockResolvedValue({
      ...identiteDeTest(),
      logos: [
        { emplacement: 'club', empreinte: 'v1' },
        { emplacement: 'evenement', empreinte: 'v1' },
      ],
    })

    monter(<EcranSalle libelle="Gymnase" tournoiId={1} />)

    expect(await screen.findByAltText(/Logo du tournoi/i)).toBeInTheDocument()
    expect(screen.getByAltText(/Logo du club organisateur/i)).toBeInTheDocument()
  })

  it('n’affiche aucun logo quand rien n’a été déposé', async () => {
    // Assertion **négative appariée** à la positive ci-dessus : les deux logos sont facultatifs
    // (« bien sûr cela reste optionnel », questionnaire A05). Un cadre vide sur un vidéoprojecteur
    // se lirait comme une image qui n'a pas chargé.
    vi.mocked(getAvancement).mockResolvedValue([])
    vi.mocked(getIdentite).mockResolvedValue(identiteDeTest())

    monter(<EcranSalle libelle="Gymnase" tournoiId={1} />)

    expect(await screen.findByTestId('classement')).toBeInTheDocument()
    expect(screen.queryByAltText(/Logo/i)).toBeNull()
  })

  it('s’allume même si l’identité n’a pas encore répondu', async () => {
    // Un écran de salle ne doit **jamais** attendre une couleur pour afficher un classement : sur un
    // vidéoprojecteur, personne n'est là pour recharger. La surface porte alors les jetons du club,
    // qui sont déjà les bons par défaut.
    vi.mocked(getAvancement).mockResolvedValue([])
    vi.mocked(getIdentite).mockReturnValue(new Promise(() => {}))

    monter(<EcranSalle libelle="Gymnase" tournoiId={1} />)

    expect(await screen.findByTestId('classement')).toBeInTheDocument()
  })
})

/** Une identité réglée en bleu — distincte du rouge du club, pour que l'assertion prouve quelque
 *  chose : avec les couleurs héritées, un habillage absent rendrait exactement le même écran. */
function identiteDeTest(): Identite {
  const jetons = { surface: '#0b6e9e', contour: '#0b6e9e', texte: '#3aa8dd', encre: '#ffffff' }
  const accent = {
    couleur: '#0b6e9e',
    sombre: jetons,
    clair: jetons,
    contraste_sur_sombre: 4.6,
    contraste_sur_clair: 4.6,
  }
  return {
    reglee: true,
    primaire: accent,
    secondaire: accent,
    logos: [],
    seuil_contour: 3,
    seuil_texte: 4.5,
    poids_logo_max_octets: 512 * 1024,
  }
}
