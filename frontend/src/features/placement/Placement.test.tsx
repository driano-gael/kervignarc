// Tests de l'écran de placement (E16US005, retour A11 du 04/08/2026).
//
// Ce que ces tests gardent, et pourquoi ils montent le composant. Le CA d'A11 est un CA de **mise
// en page** — « une cible par ligne », « un puits de réserve » : la mise en page ne se prouve pas en
// jsdom, qui ne calcule aucune grille. Ce qui se prouve, et qui est le vrai contenu de l'US, c'est
// **ce que la largeur gagnée sert à montrer** :
//
//   - le jeton porte les repères d'arbitrage (club, catégorie, blason), ceux-là mêmes sur lesquels
//     portent les deux badges de la cible — sans quoi l'organisateur lit « mixité non garantie »
//     sans savoir **qui** la cause, ce qui était exactement l'état d'avant ;
//   - un club non renseigné se dit « club inconnu », jamais « aucun club » (ADR-0014) ;
//   - un référentiel absent **n'invente rien** : pas de « Club #7 » sur quarante lignes ;
//   - la réserve distingue une mise à l'écart voulue (« en attente », neutre) d'une anomalie
//     (« sans blason », ambre) — c'est le CA « un archer en réserve doit se distinguer d'un archer
//     sans cible », déjà tenu par E03US004 et qu'on **garde ici contre une régression**.
//
// ⚠️ Le test qui compte le plus est celui du référentiel absent : c'est le seul cas où l'écran
// pourrait afficher une information **fausse** plutôt qu'incomplète, et un organisateur déplace des
// archers sur ce qu'il lit.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Blason } from '../blasons/api'
import { getBlasons } from '../blasons/api'
import type { Categorie } from '../categories/api'
import { getCategories } from '../categories/api'
import type { Club } from '../clubs/api'
import { getClubs } from '../clubs/api'
import type { Archer } from '../competition/api'
import { getArchers } from '../archers/api'
import type { Depart } from '../departs/api'
import { getDeparts } from '../departs/api'
import type { CiblePlacee, PlanDeCibles } from './api'
import { getCloisonnement, getPlanDeCibles } from './api'
import { Placement } from './Placement'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getPlanDeCibles: vi.fn(),
  getCloisonnement: vi.fn(),
}))
vi.mock('../archers/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../archers/api')>()),
  getArchers: vi.fn(),
}))
vi.mock('../departs/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/api')>()),
  getDeparts: vi.fn(),
}))
vi.mock('../clubs/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../clubs/api')>()),
  getClubs: vi.fn(),
}))
vi.mock('../categories/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../categories/api')>()),
  getCategories: vi.fn(),
}))
vi.mock('../blasons/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../blasons/api')>()),
  getBlasons: vi.fn(),
}))

// Fixtures **typées** sur les DTO : un champ manquant lu `undefined` prendrait la branche « rien à
// afficher » sans que `tsc` bronche. Même précaution que `jalons/PretADemarrer.test.tsx`.
const DEPART: Depart = {
  id: 5,
  tournoi_id: 1,
  numero: 1,
  horaire: '09:00',
  tarif_centimes: 0,
  quota: null,
  etat: 'ouvert',
}

function archer(over: Partial<Archer> = {}): Archer {
  return {
    id: 11,
    tournoi_id: 1,
    nom: 'Dupont',
    prenom: 'Marie',
    categorie_id: 3,
    cible: null,
    club_id: 7,
    handicap_officiel: null,
    handicap_surcharge: null,
    handicap: 0,
    ...over,
  }
}

const CLUB: Club = { id: 7, nom: 'Arc Club de Kervignarc' }

const CATEGORIE: Categorie = {
  id: 3,
  tournoi_id: 1,
  libelle: 'Senior 1 Femme',
  arme: 'classique',
  ages: ['S1'],
  sexe: 'F',
  blason_id: 9,
  hauteur_cm: 130,
  origine: 'ffta',
}

const BLASON: Blason = {
  id: 9,
  tournoi_id: 1,
  nom: 'Triple 40',
  taille: 40,
  capacite: 4,
  zones: ['10', '9', '8', '7', '6'],
  origine: 'ffta',
}

// Un plan minimal : une cible, un archer posé en A, réserve vide.
const CIBLE: CiblePlacee = {
  index: 1,
  capacite: 4,
  placements: [{ position: 'A', archer_id: 11, blason_id: 9, inscription_id: 21 }],
  mixite_non_garantie: false,
  cloisonnement_non_respecte: false,
}

const PLAN: PlanDeCibles = { depart_id: 5, cibles: [CIBLE], conflits: [] }

function creerClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function monter(enfants: ReactNode) {
  return render(<QueryClientProvider client={creerClient()}>{enfants}</QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getDeparts).mockResolvedValue([DEPART])
  vi.mocked(getPlanDeCibles).mockResolvedValue(PLAN)
  vi.mocked(getCloisonnement).mockResolvedValue({ cloisonnement: 'aucun' })
  vi.mocked(getArchers).mockResolvedValue([archer()])
  vi.mocked(getClubs).mockResolvedValue([CLUB])
  vi.mocked(getCategories).mockResolvedValue([CATEGORIE])
  vi.mocked(getBlasons).mockResolvedValue([BLASON])
})

// Le départ se choisit par le `select` : le plan n'est monté qu'ensuite.
async function choisirLeDepart() {
  const selecteur = await screen.findByLabelText('Départ à placer')
  const { default: userEvent } = await import('@testing-library/user-event')
  await userEvent.selectOptions(selecteur, '5')
}

describe('Placement — le jeton porte les repères d’arbitrage (E16US005)', () => {
  it('CA — club, catégorie et blason sont lisibles sous le nom, sans quitter le plan', async () => {
    // Avant cette US, la vignette ne portait que « Marie Dupont » : les badges « mixité non
    // garantie » et « cloisonnement non respecté » désignaient une cible sans jamais dire lequel de
    // ses quatre occupants en était la cause.
    monter(<Placement tournoiId={1} />)
    await choisirLeDepart()

    expect(await screen.findByText('Marie Dupont')).toBeInTheDocument()
    expect(
      await screen.findByText('Arc Club de Kervignarc · Senior 1 Femme · Triple 40'),
    ).toBeInTheDocument()
  })

  it('un club non renseigné se dit « club inconnu » (ADR-0014)', async () => {
    // C'est **la cause** du badge de mixité que le serveur pose : le serveur traite `NULL` comme
    // *indécidable*, l'écran doit le dire dans les mêmes termes. « Aucun club » serait faux — en
    // FFTA tout licencié en a un.
    vi.mocked(getArchers).mockResolvedValue([archer({ club_id: null })])
    monter(<Placement tournoiId={1} />)
    await choisirLeDepart()

    expect(await screen.findByText(/club inconnu/)).toBeInTheDocument()
    expect(screen.queryByText(/aucun club/i)).toBeNull()
  })

  it('un référentiel injoignable n’invente aucun libellé', async () => {
    // Le cas du LAN qui tousse, et celui du premier rendu (les référentiels arrivent après le plan).
    // Le nom reste lisible, les repères se taisent : incomplet plutôt que faux.
    vi.mocked(getClubs).mockRejectedValue(new Error('LAN coupé'))
    vi.mocked(getCategories).mockRejectedValue(new Error('LAN coupé'))
    vi.mocked(getBlasons).mockRejectedValue(new Error('LAN coupé'))
    monter(<Placement tournoiId={1} />)
    await choisirLeDepart()

    expect(await screen.findByText('Marie Dupont')).toBeInTheDocument()
    expect(screen.queryByText(/#7|#3|#9/)).toBeNull()
  })
})

describe('Placement — le puits de réserve (E16US005, CA repris d’E03US004)', () => {
  it('CA — un archer mis de côté se distingue d’un archer que rien ne peut placer', async () => {
    // Le CA d'A11 dit « un archer en réserve n'est **pas** placé — il doit se distinguer d'un archer
    // sans cible ». Les deux vivent dans la même liste : ce qui les sépare est la **raison**, et le
    // registre visuel qui l'accompagne (neutre contre ambre, `DV-03`).
    vi.mocked(getArchers).mockResolvedValue([
      archer(),
      archer({ id: 12, prenom: 'Luc', nom: 'Martin' }),
    ])
    vi.mocked(getPlanDeCibles).mockResolvedValue({
      ...PLAN,
      cibles: [{ ...CIBLE, placements: [] }],
      conflits: [
        { archer_id: 11, raison: 'en_reserve', inscription_id: 21 },
        { archer_id: 12, raison: 'sans_blason', inscription_id: 22 },
      ],
    })
    monter(<Placement tournoiId={1} />)
    await choisirLeDepart()

    expect(await screen.findByText('en attente')).toBeInTheDocument()
    expect(screen.getByText('sans blason')).toBeInTheDocument()
    // L'anomalie porte le registre ambre, la mise à l'écart non : c'est ce qui les distingue à
    // l'œil, et un futur correctif qui uniformiserait la classe effacerait la distinction.
    expect(screen.getByText('sans blason')).toHaveClass('reserve__raison--anomalie')
    expect(screen.getByText('en attente')).not.toHaveClass('reserve__raison--anomalie')
  })

  it('un archer en réserve garde ses repères, sans blason', async () => {
    // Il n'est posé nulle part : aucun carton ne lui est attribué. Le club et la catégorie, eux,
    // restent utiles — « sans blason » + la catégorie dit **laquelle** n'a pas de carton à sa
    // hauteur, ce qui est le geste correctif.
    vi.mocked(getPlanDeCibles).mockResolvedValue({
      ...PLAN,
      cibles: [{ ...CIBLE, placements: [] }],
      conflits: [{ archer_id: 11, raison: 'sans_blason', inscription_id: 21 }],
    })
    monter(<Placement tournoiId={1} />)
    await choisirLeDepart()

    expect(await screen.findByText('Arc Club de Kervignarc · Senior 1 Femme')).toBeInTheDocument()
    expect(screen.queryByText(/Triple 40/)).toBeNull()
  })
})
