// Tests de **montage** de la vue publique des tableaux (E07US005).
//
// Ce fichier existe à cause d'un défaut précis, et il vaut mieux le dire que le paraphraser : la
// première version de `VueTableaux` dérivait la liste des archers suivis **dans le sélecteur
// Zustand** (`s.suivis.filter(...).map(...)`). Un sélecteur qui rend un tableau neuf à chaque appel
// rend `getSnapshot` instable pour `useSyncExternalStore` — donc **boucle de rendu infinie** en
// Zustand v5 / React 19, y compris avec zéro archer suivi. La fonctionnalité était inutilisable, et
// **aucune porte mécanique ne pouvait le voir** : ni `tsc`, ni `eslint`, ni les 17 tests de logique
// pure de `presentation.test.ts`, qui n'appellent jamais React.
//
// Le dépôt portait pourtant déjà le correctif, sur le **même store**, dans la feature voisine
// (`suivi/VueSuivi.tsx`, « correctif de revue A »). Ce qui manquait n'était pas la connaissance,
// c'était un test qui **monte le composant**. C'est tout l'objet de ce fichier — et la leçon
// réutilisable : une feature front sans un seul rendu testé a un angle mort de cette taille.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSessionSuivisStore } from '../../shared/stores/sessionSuivisStore'
import type { DuelPublic, TableauPublic, Tableaux } from './api'
import { getTableaux } from './api'
import { VueTableaux } from './VueTableaux'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getTableaux: vi.fn(),
}))

function duel(patch: Partial<DuelPublic> = {}): DuelPublic {
  return {
    numero: 1,
    tour: 1,
    libelle: 'Demi-finale',
    place_en_jeu: null,
    plage: [1, 4],
    haut: { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' },
    bas: { archer_id: 2, nom: 'DURAND', prenom: 'Eve' },
    est_bye: false,
    points_haut: null,
    points_bas: null,
    vainqueur: null,
    termine: false,
    validee: false,
    ...patch,
  }
}

function reponse(duels: DuelPublic[] = [duel()]): Tableaux {
  const tableau: TableauPublic = {
    phase_id: 1,
    ordre: 2,
    type: 'elimination_directe',
    effectif: 4,
    taille: 4,
    nb_tours: 2,
    est_termine: false,
    duels,
    podium: [],
  }
  return { tournoi_id: 1, tableaux: [tableau] }
}

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

describe('VueTableaux — montage', () => {
  beforeEach(() => {
    vi.mocked(getTableaux).mockResolvedValue(reponse())
    useSessionSuivisStore.setState({ suivis: [] })
  })

  it('se monte et rend l’arbre sans boucler, sans aucun archer suivi', async () => {
    // Le cas le plus banal — et celui qui bouclait. `[].filter().map()` est déjà une référence
    // neuve : le défaut ne demandait même pas qu'on suive quelqu'un pour se déclencher.
    render(<Cadre enfants={<VueTableaux tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByText(/Demi-finale/)).toBeInTheDocument())
    expect(screen.getByText(/MARTIN/)).toBeInTheDocument()
  })

  it('se monte et ouvre sur « Mon chemin » quand on suit un archer', async () => {
    useSessionSuivisStore.setState({ suivis: [{ archerId: 1, tournoiId: 1 }] })

    render(<Cadre enfants={<VueTableaux tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByText(/MARTIN/)).toBeInTheDocument())
    // « Mon chemin » est la lecture par défaut dès qu'on suit quelqu'un (D-09) : c'est le nom de
    // l'archer qui titre sa carte, pas un en-tête de tour.
    expect(screen.getByText('Luc MARTIN')).toBeInTheDocument()
  })

  it('n’ouvre pas de requête et le dit quand aucun tableau n’existe', async () => {
    vi.mocked(getTableaux).mockResolvedValue({ tournoi_id: 1, tableaux: [] })

    render(<Cadre enfants={<VueTableaux tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByText(/Pas encore de tableau/)).toBeInTheDocument())
  })

  it('sur l’écran de salle, n’affiche aucune commande', async () => {
    // CA E07US004 : **aucune interaction** sur un écran projeté. Ni bascule de lecture, ni
    // sélecteur de phase — un bouton que personne ne peut actionner est un défaut, pas un détail.
    useSessionSuivisStore.setState({ suivis: [{ archerId: 1, tournoiId: 1 }] })

    render(<Cadre enfants={<VueTableaux tournoiId={1} interactif={false} />} />)

    await waitFor(() => expect(screen.getByText(/Demi-finale/)).toBeInTheDocument())
    expect(screen.queryByRole('button')).toBeNull()
    // Et c'est bien l'arbre complet qui s'affiche, pas « mon chemin » : personne ne suit d'archer
    // devant un projecteur.
    expect(screen.getByText(/MARTIN/)).toBeInTheDocument()
  })
})
