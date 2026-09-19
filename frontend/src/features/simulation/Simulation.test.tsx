// Rendu du cockpit de simulation — le test qui manquait quand son contrat a changé (E06US009).
//
// ⚠️ **Pourquoi ce fichier existe.** `EtatSession` est un miroir écrit à la main d'un modèle
// Pydantic, et `fetchJson<T>` transtype sans valider : quand E06US009 a changé le contrat, `tsc`
// est resté vert, `vitest` aussi (zéro test ici) et la porte a rendu 14/14 — sur une appli admin
// qui tombait en page blanche, faute d'`ErrorBoundary`. Les cinq axes de revue l'ont vu, aucun
// outil ne le pouvait. Ce qu'on garde ici est donc **le déréférencement**, pas la mise en page.

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { EtatSession } from './api'
import { Simulation } from './Simulation'

vi.mock('../../shared/realtime/RealtimeClient', () => ({
  RealtimeClient: class {
    connecter() {}
    fermer() {}
  },
}))

const mutationInerte = { mutate: vi.fn(), isPending: false, error: null }

vi.mock('./hooks', async () => {
  const reel = await vi.importActual<typeof import('./hooks')>('./hooks')
  return {
    ...reel,
    useEtatSimulation: vi.fn(),
    useDemarrerSimulation: vi.fn(),
    useDetailArcher: () => ({ data: undefined }),
    useAvancer: () => mutationInerte,
    useTerminer: () => mutationInerte,
    usePause: () => mutationInerte,
    useReprendre: () => mutationInerte,
    useSaisirVolee: () => mutationInerte,
    useDesignerVainqueur: () => mutationInerte,
  }
})

const { useDemarrerSimulation, useEtatSimulation } = await import('./hooks')

function ligne(archerId: number, nom: string, total: number) {
  return {
    archer_id: archerId,
    nom,
    prenom: 'P',
    club_libelle: null,
    categorie_libelle: 'Senior 1 Homme',
    categorie_id: 3,
    total,
    nb_dix: 0,
    nb_neuf: 0,
    rang_scratch: 1,
    rang_categorie: 1,
    statut: 'en_lice',
    volees: [],
  }
}

/** Deux créneaux **réellement peuplés** : à un seul, « le premier partout » resterait invisible. */
const ETAT = {
  session_id: 7,
  tournoi_id: 1,
  tournoi_nom: 'Salle 18m',
  graine: 42,
  etat_pilote: 'en_pause',
  etape: 'qualification',
  progression: { volees_faites: 1, volees_total: 4, duels_faits: 0, duels_total: 0 },
  creneaux: [
    {
      depart_id: 41,
      libelle: 'Départ n°1 — 09:00',
      classement: { lignes: [ligne(1, 'MARTIN', 30)] },
      tableaux: [],
    },
    {
      depart_id: 42,
      libelle: 'Départ n°2 — 14:00',
      classement: { lignes: [ligne(2, 'CADIOU', 28)] },
      tableaux: [],
    },
  ],
  prochaine_unite: null,
} as unknown as EtatSession

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

/** Ouvre le cockpit : le composant n'expose pas sa session, on passe donc par le vrai geste. */
async function ouvrirLeCockpit() {
  vi.mocked(useEtatSimulation).mockReturnValue({ data: ETAT } as ReturnType<
    typeof useEtatSimulation
  >)
  vi.mocked(useDemarrerSimulation).mockReturnValue({
    mutate: (_entree: unknown, options?: { onSuccess?: (etat: EtatSession) => void }) =>
      options?.onSuccess?.(ETAT),
    isPending: false,
    error: null,
  } as unknown as ReturnType<typeof useDemarrerSimulation>)
  render(<Cadre enfants={<Simulation tournoiId={1} />} />)
  await userEvent.click(screen.getByRole('button', { name: /Démarrer la simulation/ }))
}

describe('Simulation — le cockpit rejoue chaque créneau (E06US009)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('rend un classement par créneau, titré de son libellé', async () => {
    await ouvrirLeCockpit()

    // ⚠️ L'assertion porte sur les DEUX archers : un cockpit resté sur « le » premier créneau
    // afficherait MARTIN seul, et un test qui ne compterait que les titres le laisserait passer.
    expect(screen.getByText(/Départ n°1 — 09:00/)).toBeInTheDocument()
    expect(screen.getByText(/Départ n°2 — 14:00/)).toBeInTheDocument()
    // `TableClassement` compose « NOM Prénom » dans un seul nœud — d'où le motif, pas l'égalité.
    expect(screen.getByText(/MARTIN/)).toBeInTheDocument()
    expect(screen.getByText(/CADIOU/)).toBeInTheDocument()
  })

  it('ne déréférence aucun champ absent du contrat serveur', async () => {
    // Le test de régression pur : avant correction, `etat.classement.lignes` levait un TypeError
    // ici même — et comme `frontend/src` n'a aucun ErrorBoundary, c'est toute l'appli qui tombait.
    await expect(ouvrirLeCockpit()).resolves.not.toThrow()
    expect(screen.queryByText(/Chargement/)).not.toBeInTheDocument()
  })
})
