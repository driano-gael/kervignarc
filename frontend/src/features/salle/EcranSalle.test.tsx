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
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Depart } from '../departs/api'
import { getDeparts } from '../departs/api'
import type { Phase } from '../phases/api'
import { getAvancement } from '../phases/api'
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
