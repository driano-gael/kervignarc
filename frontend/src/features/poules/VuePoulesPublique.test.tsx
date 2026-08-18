// Tests de **montage** de la vue publique des poules (E05US031, ADR-0089).
//
// ⚠️ **Écrits en correctif de revue** (axes B, C1 et C2) — cf. le récit dans
// `VueSuissePublique.test.tsx`. Ce que ces cas gardent en propre, c'est le CA « une poule montre
// **tous ses tours** » : c'est la forme du round-robin qui sert l'historique ici, sans navigation à
// bâtir, et rien ne le vérifiait.
//
// Les cas dérivent de `docs/fonctionnel/E05US031.md` § scénarios 2 et 6, pas de l'implémentation.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EtatPoules, PoulePublique, RencontrePublique } from './api'
import { getEtatPoules } from './api'
import { VuePoulesPublique } from './VuePoulesPublique'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getEtatPoules: vi.fn(),
}))

const MARTIN = { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' }
const DURAND = { archer_id: 2, nom: 'DURAND', prenom: 'Aline' }
const PETIT = { archer_id: 3, nom: 'PETIT', prenom: 'Jo' }

function rencontre(
  patch: Partial<RencontrePublique> & Pick<RencontrePublique, 'numero' | 'tour'>,
): RencontrePublique {
  return {
    poule: 1,
    couloirs: null,
    haut: MARTIN,
    bas: DURAND,
    points_haut: null,
    points_bas: null,
    vainqueur: null,
    termine: false,
    validee: false,
    desynchronisee: false,
    ...patch,
  }
}

function poule(patch: Partial<PoulePublique> = {}): PoulePublique {
  return {
    numero: 1,
    membres: [MARTIN, DURAND, PETIT],
    bloc: null,
    rencontres: [
      // ⚠️ Volontairement **dans le désordre** : rien ne promet l'ordre de la réponse JSON, et le
      // regroupement par tour ne doit ni s'y fier ni perdre une rencontre.
      rencontre({ numero: 3, tour: 2, haut: DURAND, bas: PETIT }),
      rencontre({
        numero: 1,
        tour: 1,
        termine: true,
        validee: true,
        points_haut: 6,
        points_bas: 2,
        vainqueur: 'haut',
      }),
      rencontre({ numero: 2, tour: 2, haut: MARTIN, bas: PETIT }),
    ],
    classement: [],
    qualifies: [],
    barrage_requis: false,
    ...patch,
  }
}

function etat(patch: Partial<EtatPoules> = {}): EtatPoules {
  return {
    phase_id: 7,
    repartition: { effectif: 3, taille_visee: 3, nb_poules: 1, tailles: [3] },
    poules: [poule()],
    conflits: [],
    ...patch,
  }
}

function monter(noeud: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{noeud}</QueryClientProvider>)
}

beforeEach(() => vi.mocked(getEtatPoules).mockReset())

describe('VuePoulesPublique — tous les tours, dans l’ordre', () => {
  it('groupe les rencontres par tour et n’en perd aucune', async () => {
    // CA du 18/08 : « une poule montre tous ses tours ». L'historique est gratuit ici — c'est la
    // forme du round-robin qui le sert, pas une navigation.
    vi.mocked(getEtatPoules).mockResolvedValue(etat())

    monter(<VuePoulesPublique tournoiId={1} phaseId={7} />)

    expect(await screen.findByRole('heading', { name: 'Tour 1' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Tour 2' })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  it('affiche le score dès qu’il existe, et le vainqueur seulement une fois validé', async () => {
    // Le score est ce que la salle voit sur les cibles ; le vainqueur en gras engage un résultat
    // qu'une correction peut encore renverser.
    vi.mocked(getEtatPoules).mockResolvedValue(
      etat({
        poules: [
          poule({
            rencontres: [
              rencontre({
                numero: 1,
                tour: 1,
                termine: true,
                points_haut: 6,
                points_bas: 2,
                vainqueur: 'haut',
              }),
            ],
          }),
        ],
      }),
    )

    monter(<VuePoulesPublique tournoiId={1} phaseId={7} />)

    expect(await screen.findByText('6 — 2')).toBeInTheDocument()
    expect(screen.getByText(/en attente de validation/)).toBeInTheDocument()
  })

  it('dit qu’une poule est composée mais pas encore appariée', async () => {
    // Sans ce mot, une poule sans rencontre est indiscernable d'une poule cassée.
    vi.mocked(getEtatPoules).mockResolvedValue(etat({ poules: [poule({ rencontres: [] })] }))

    monter(<VuePoulesPublique tournoiId={1} phaseId={7} />)

    expect(await screen.findByText(/pas encore appariées/)).toBeInTheDocument()
  })

  it('annonce une poule dont les cibles ne sont pas posées', async () => {
    vi.mocked(getEtatPoules).mockResolvedValue(
      etat({ conflits: [{ poule: 1, raison: 'salle trop petite' }] }),
    )

    monter(<VuePoulesPublique tournoiId={1} phaseId={7} />)

    expect(await screen.findByText(/n’a pas encore de cibles attribuées/)).toBeInTheDocument()
  })
})

describe('VuePoulesPublique — « mes archers » (ADR-0079)', () => {
  it('retient une poule où un archer suivi est MEMBRE, même sans rencontre appariée', async () => {
    // ⚠️ Le choix que garde ce cas : le filtre porte sur les **membres**, pas sur les rencontres.
    // Filtrer sur les rencontres ferait disparaître de l'écran l'archer qu'on suit précisément
    // parce qu'il va y tirer.
    vi.mocked(getEtatPoules).mockResolvedValue(etat({ poules: [poule({ rencontres: [] })] }))

    monter(<VuePoulesPublique tournoiId={1} phaseId={7} mode="suivis" suivis={[3]} />)

    expect(await screen.findByRole('heading', { name: /Poule 1/ })).toBeInTheDocument()
  })

  it('nomme « aucun de vos archers ici » distinctement de « pas encore composées »', async () => {
    // Deux branches, deux messages : l'un décrit le tournoi, l'autre le filtre. C'est la règle
    // « chaque écran nomme son propre vide ».
    vi.mocked(getEtatPoules).mockResolvedValue(etat())

    monter(<VuePoulesPublique tournoiId={1} phaseId={7} mode="suivis" suivis={[99]} />)

    expect(await screen.findByText(/Aucun des archers que vous suivez/)).toBeInTheDocument()
    expect(screen.queryByText(/pas encore composées/)).toBeNull()
  })
})
