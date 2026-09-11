// La poignée de réouverture du panneau de routage en duels (E16US018).
//
// ⚠️ Elle existe parce que le panneau se referme désormais **tout seul** : sans elle, une fermeture
// automatique serait irréversible pour ce duel — c'est l'écran qui dit à un repêché qu'il repart,
// et à un sorti quelle place il prend. La qualification l'avait depuis E04US018, les duels non.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import type { Duel, Tableau } from './api'
import { SaisieDuels } from './SaisieDuels'

const PHASE = { id: 901, ordre: 1, type: 'elimination_directe' }

const DUEL: Duel = {
  numero: 1,
  tour: 1,
  place_en_jeu: null,
  haut: { archer_id: 11, nom: 'MARTIN', prenom: 'Luc' },
  bas: { archer_id: 22, nom: 'DURAND', prenom: 'Anne' },
  est_bye: false,
  mode: 'sets',
  nb_manches: 5,
  nb_fleches_par_volee: 3,
  points_pour_gagner: 6,
  zones: ['10', '9', '8', 'M'],
  validee_par: null,
  manches: [],
  barrage: null,
  resultat: {
    points_haut: 6,
    points_bas: 0,
    vainqueur: 'haut',
    termine: true,
    barrage_requis: false,
  },
}

// ⚠️ **Deux duels, pas un** : le CA dit que la poignée rouvre le **dernier** duel validé. Avec un
// seul duel au décor, une régression qui garderait les duellistes du premier passerait inaperçue
// (relevé en revue) — et c'est justement un état qui survit à la fermeture.
const DUEL_2: Duel = {
  ...DUEL,
  numero: 2,
  haut: { archer_id: 33, nom: 'PETIT', prenom: 'Jean' },
  bas: { archer_id: 44, nom: 'ROUX', prenom: 'Zoe' },
}

const TABLEAU: Tableau = {
  effectif: 4,
  taille: 4,
  nb_tours: 1,
  est_termine: false,
  duels: [DUEL, DUEL_2],
  podium: [],
}

// La validation « part » : c'est la condition qui déclenche la bascule (hors-ligne, on ne route pas
// sur une avancée qui n'a pas eu lieu).
const VALIDER = {
  mutate: (
    _vars: unknown,
    options?: { onSuccess?: (d: { validation_en_attente: boolean }) => void },
  ) => options?.onSuccess?.({ validation_en_attente: false }),
  isPending: false,
  isError: false,
  error: null,
}
const MUTATION = { mutate: vi.fn(), isPending: false, isError: false, error: null }

vi.mock('./hooks', () => ({
  usePhases: () => ({ data: [PHASE], isError: false, isSuccess: true, error: null }),
  useTableau: () => ({ isPending: false, isError: false, data: TABLEAU, error: null }),
  useDuel: (_t: number, _p: number, matchNumero: number) => ({
    isPending: false,
    isError: false,
    isSuccess: true,
    data: matchNumero === 2 ? DUEL_2 : DUEL,
    error: null,
  }),
  useDuelsEnAttente: () => 0,
  useRejeuDuelsHorsLigne: () => undefined,
  useSaisirManche: () => MUTATION,
  useSaisirBarrage: () => MUTATION,
  useValiderDuel: () => VALIDER,
}))

// Le panneau lui-même est testé dans `features/routage` : ici on ne juge que son accessibilité
// depuis la liste des duels.
vi.mock('../routage/hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../routage/hooks')>()),
  useRoutage: () => ({
    data: { phase_id: 901, archers: [], avis_permanent: false },
    isLoading: false,
    isError: false,
    error: null,
  }),
}))
vi.mock('../departs/hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/hooks')>()),
  useDeparts: () => ({ data: [{ id: 41, numero: 1, statut: 'en_cours' }] }),
}))

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(<SaisieDuels tournoiId={1} departId={41} />, { wrapper: Enveloppe })
}

const panneau = (numero: number) =>
  screen.queryByRole('region', { name: `Où tire-t-on ensuite ? — duel n°${numero}` })

describe('SaisieDuels — rouvrir le panneau de routage', () => {
  async function validerLeDuel(utilisateur: ReturnType<typeof userEvent.setup>, nom: RegExp) {
    await utilisateur.click(screen.getByRole('button', { name: nom }))
    await utilisateur.click(screen.getByRole('button', { name: 'Valider le duel' }))
  }

  it('offre la poignée après un duel validé, et rouvre le panneau autant de fois qu’on veut', async () => {
    const utilisateur = userEvent.setup()
    monter()
    await utilisateur.selectOptions(
      screen.getByRole('combobox', { name: 'Phase de tableau à scorer' }),
      String(PHASE.id),
    )

    // Aucun duel validé sur cette tablette : rien à rouvrir, donc pas de lien.
    expect(screen.queryByRole('button', { name: /Où tire-t-on ensuite/ })).toBeNull()

    await validerLeDuel(utilisateur, /MARTIN/)
    expect(panneau(1)).not.toBeNull()

    await utilisateur.click(screen.getByRole('button', { name: 'Retour à la liste' }))
    expect(panneau(1)).toBeNull()

    await utilisateur.click(screen.getByRole('button', { name: /Où tire-t-on ensuite/ }))
    expect(panneau(1)).not.toBeNull()

    // Deux fois : la fermeture ne consomme pas la poignée.
    await utilisateur.click(screen.getByRole('button', { name: 'Retour à la liste' }))
    await utilisateur.click(screen.getByRole('button', { name: /Où tire-t-on ensuite/ }))
    expect(panneau(1)).not.toBeNull()
  })

  it('rouvre le DERNIER duel validé, et le nomme', async () => {
    // ⚠️ Le cœur du CA : `routageDe` survit à la fermeture, donc il peut dater. À 11 h, la poignée
    // ne doit pas rouvrir le duel de 9 h 40 sous un libellé muet qui promet celui qu'on regarde.
    const utilisateur = userEvent.setup()
    monter()
    await utilisateur.selectOptions(
      screen.getByRole('combobox', { name: 'Phase de tableau à scorer' }),
      String(PHASE.id),
    )

    await validerLeDuel(utilisateur, /MARTIN/)
    await utilisateur.click(screen.getByRole('button', { name: 'Retour à la liste' }))
    await validerLeDuel(utilisateur, /PETIT/)
    await utilisateur.click(screen.getByRole('button', { name: 'Retour à la liste' }))

    expect(screen.getByRole('button', { name: 'Où tire-t-on ensuite ? — duel n°2' })).not.toBeNull()
    await utilisateur.click(screen.getByRole('button', { name: /Où tire-t-on ensuite/ }))

    expect(panneau(2)).not.toBeNull()
    expect(panneau(1)).toBeNull()
  })
})
