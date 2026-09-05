// Tests de rendu du plan de duels (E16US005).
//
// ⚠️ `duels/Duels.tsx` est le jumeau de `placement/Placement.tsx` — quatre composants recopiés
// (`DETTE-085`) : tant qu'aucun test ne montait cet écran, un changement appliqué au seul plan de
// qualification **compilait, passait le lint et passait la suite**. C'est ce qui s'est produit — la
// fabrique calculait les repères, `JetonArcher` rendait toujours le nom nu : `tsc` ne voit pas une
// propriété fournie et jamais consommée. Le garde-fou est **proportionné à la dette assumée** : on
// rend la divergence détectable, on ne remonte rien dans `shared/`.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getArchers } from '../archers/api'
import type { Blason } from '../blasons/api'
import { getBlasons } from '../blasons/api'
import type { Categorie } from '../categories/api'
import { getCategories } from '../categories/api'
import type { Club } from '../clubs/api'
import { getClubs } from '../clubs/api'
import type { Archer } from '../competition/api'
import type { Depart } from '../departs/api'
import { getDeparts } from '../departs/api'
import type { Phase } from '../phases/api'
import { getAvancement } from '../phases/api'
import type { CiblePlaceeDuel, PlanDeDuels } from './api'
import { getPlanDeDuels } from './api'
import { Duels } from './Duels'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getPlanDeDuels: vi.fn(),
}))
vi.mock('../archers/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../archers/api')>()),
  getArchers: vi.fn(),
}))
vi.mock('../departs/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/api')>()),
  getDeparts: vi.fn(),
}))
vi.mock('../phases/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../phases/api')>()),
  getAvancement: vi.fn(),
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

const DEPART: Depart = {
  id: 5,
  tournoi_id: 1,
  numero: 1,
  horaire: '09:00',
  tarif_centimes: 0,
  quota: null,
  etat: 'ouvert',
}

const ARCHER: Archer = {
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

// Une phase de **tableau** : le seul type que l'écran propose au placement des duellistes.
const PHASE: Phase = {
  id: 30,
  depart_id: 5,
  ordre: 1,
  type: 'elimination_directe',
  statut: 'en_cours',
  sources: [],
  effectif: 8,
  barrage_jusqu_au: null,
  profondeur: null,
  poules: null,
  big_shoot_off: null,
  suisse: null,
  colline: null,
  decoupage: null,
}

const CIBLE: CiblePlaceeDuel = {
  index: 1,
  capacite: 4,
  placements: [{ position: 'A', archer_id: 11, blason_id: 9, inscription_id: 21 }],
  adjacence_non_garantie: false,
  cloisonnement_non_respecte: false,
}

const PLAN: PlanDeDuels = {
  phase_id: 30,
  tour: 1,
  cibles: [CIBLE],
  conflits: [],
  duels_separes: [],
}

function creerClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function monter(enfants: ReactNode) {
  return render(<QueryClientProvider client={creerClient()}>{enfants}</QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getDeparts).mockResolvedValue([DEPART])
  vi.mocked(getAvancement).mockResolvedValue([PHASE])
  vi.mocked(getPlanDeDuels).mockResolvedValue(PLAN)
  vi.mocked(getArchers).mockResolvedValue([ARCHER])
  vi.mocked(getClubs).mockResolvedValue([CLUB])
  vi.mocked(getCategories).mockResolvedValue([CATEGORIE])
  vi.mocked(getBlasons).mockResolvedValue([BLASON])
})

// Le plan n'est monté qu'une fois la phase de tableau choisie.
async function choisirLaPhase() {
  const selecteur = await screen.findByLabelText('Phase de tableau à placer')
  await userEvent.selectOptions(selecteur, '30')
}

describe('Plan de duels — alignement sur le plan de cibles (E16US005)', () => {
  it('CA — le jeton d’un duelliste porte ses repères, comme en qualification', async () => {
    // **Le test qui compte.** Sans lui, `Duels.tsx` peut calculer `reperes`, monter les trois
    // référentiels et ne jamais les rendre : c'est arrivé, et rien de mécanique ne l'a vu.
    monter(<Duels tournoiId={1} />)
    await choisirLaPhase()

    // ⚠️ Les assertions portent sur les **classes**, pas seulement sur la présence du texte. Le
    // défaut d'origine avait deux moitiés — repères absents *et* typographie du nom perdue (le
    // `<span className="jeton__nom">` non émis) —, et une assertion `toBeInTheDocument()` seule
    // passait sur la seconde : elle rend le nœud porteur du texte, enveloppé ou non.
    expect(await screen.findByText('Marie Dupont')).toHaveClass('jeton__nom')
    expect(await screen.findByText('Arc Club de Kervignarc')).toHaveClass('jeton__reperes')
    expect(await screen.findByText('Senior 1 Femme · Triple 40')).toHaveClass('jeton__reperes')
    expect(screen.getByText('Marie Dupont').closest('.jeton')).toHaveAttribute(
      'title',
      'Arc Club de Kervignarc · Senior 1 Femme · Triple 40 · glisser pour déplacer',
    )
  })

  it('la lettre du couloir est rendue sur une case occupée, comme en qualification', async () => {
    // Ajoutée aux duels par cette US (le placement la rendait depuis E03US011). En bandes, c'est
    // elle qui rattache un jeton à sa colonne quand les capacités diffèrent — et la fiche de
    // recette en fait un point à vérifier. Rien ne la gardait.
    monter(<Duels tournoiId={1} />)
    await choisirLaPhase()

    const couloirA = await screen.findByLabelText('Couloir de tir A')
    expect(within(couloirA).getByText('A')).toHaveClass('case__position')
  })

  it('la grille de couloirs est dérivée du plan, ici aussi', async () => {
    // ⚠️ **Le miroir du garde-fou de `Placement.test.tsx`.** `couloirs` et son `Math.min` sont
    // recopiés dans les deux écrans (`DETTE-085`). Ne les tester que d'un côté, c'est reproduire
    // dans le garde-fou même le mécanisme qu'il ferme : E01US019 retournera les cas du placement,
    // touchera un fichier, et laissera le plan de duels plafonné à 4 en silence.
    vi.mocked(getPlanDeDuels).mockResolvedValue({
      ...PLAN,
      cibles: [{ ...CIBLE, capacite: 2, placements: [] }],
    })
    monter(<Duels tournoiId={1} />)
    await choisirLaPhase()

    await screen.findByText('Cible 1')
    expect(
      (document.querySelector('.placement__cibles') as HTMLElement).style.getPropertyValue(
        '--couloirs',
      ),
    ).toBe('2')
  })

  it('la réserve des duels distingue une mise à l’écart d’une anomalie', async () => {
    // Non-régression du défaut historique d'E03US007 : la copie `RaisonConflit` des duels était
    // restée à trois valeurs quand le serveur en émettait quatre, et la réserve s'affichait **sans
    // motif**. Le vocabulaire est mutualisé depuis, mais rien ne gardait le **rendu** de ce côté.
    vi.mocked(getPlanDeDuels).mockResolvedValue({
      ...PLAN,
      cibles: [{ ...CIBLE, placements: [] }],
      conflits: [
        { archer_id: 11, raison: 'en_reserve', inscription_id: 21 },
        { archer_id: 12, raison: 'sans_blason', inscription_id: 22 },
      ],
    })
    monter(<Duels tournoiId={1} />)
    await choisirLaPhase()

    expect(await screen.findByText('en attente')).toBeInTheDocument()
    expect(screen.getByText('sans blason')).toHaveClass('reserve__raison--anomalie')
    expect(screen.getByText('en attente')).not.toHaveClass('reserve__raison--anomalie')
  })
})
