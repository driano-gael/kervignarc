// Tests de rendu du plan de duels (E16US005).
//
// **Pourquoi ce fichier existe, et pourquoi il n'existait pas avant.** `duels/Duels.tsx` est le
// jumeau de `placement/Placement.tsx` — quatre composants recopiés (`DETTE-085`). Tant qu'aucun test
// ne montait cet écran, un changement appliqué au seul plan de qualification **compilait, passait le
// lint et passait la suite**. C'est exactement ce qui s'est produit à la première rédaction
// d'E16US005 : la fabrique de jeton calculait les repères, les trois référentiels étaient montés, le
// type portait le champ… et `JetonArcher` rendait toujours `{jeton.nom}` nu. `tsc` ne voit rien —
// une propriété *fournie* et jamais *consommée* n'est pas une erreur de type — et les quatre
// documents de suivi affirmaient l'inverse. Trois axes de revue l'ont rattrapé ; ce fichier fait
// que la prochaine fois, c'est un test rouge.
//
// Le garde-fou est **proportionné à la dette assumée** : on ne remonte pas les composants dans
// `shared/` (ce serait un remède structurel en douce, cf. `DETTE-085`), on rend la divergence
// **détectable**. Deux cas suffisent : ce que l'US ajoute, et la non-régression historique.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
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

const PLAN: PlanDeDuels = { phase_id: 30, cibles: [CIBLE], conflits: [], duels_separes: [] }

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

    expect(await screen.findByText('Marie Dupont')).toBeInTheDocument()
    expect(
      await screen.findByText('Arc Club de Kervignarc · Senior 1 Femme · Triple 40'),
    ).toBeInTheDocument()
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
