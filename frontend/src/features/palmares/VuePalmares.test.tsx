// Tests de **montage** du palmarès (E06US004, centrage ajouté par E16US004).
//
// Un seul invariant est verrouillé ici, mais c'est celui qui n'a pas de recours s'il tombe :
// **le centrage « mes archers » ne touche jamais les podiums**.
//
// C'est un garde-fou qui *interdit* un comportement, donc exactement la sorte de règle qu'un
// refactor casse en silence — on n'ajoute pas un bug, on retire une exception. La revue d'E16US004
// l'a relevé : la règle était énoncée dans une docstring et appliquée dans le JSX, sans un seul
// test. Un podium amputé de ses médaillés ne répond plus à « qui a gagné », la seule question que
// cet écran serve ; et le spectateur qui ne suit aucun médaillé est précisément celui pour qui la
// question se pose.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
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
    origine: 'tableau',
    statut: 'classe',
    decerne: true,
    en_lice: false,
    ...patch,
  } as LignePalmares
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

const PALMARES: Palmares = {
  tournoi_id: 1,
  podiums: [{ categorie_id: 3, categorie_libelle: 'Senior 1 Homme', lignes: [MEDAILLE] }],
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
    const classement = screen.getByRole('table')
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
    expect(screen.queryByText(/Aucun archer classé/)).toBeNull()
    // Et le podium, lui, reste affiché : ce vide-là ne l'ampute pas non plus.
    expect(screen.getByText(/CHAMPION/)).toBeInTheDocument()
  })
})
