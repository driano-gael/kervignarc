// Test de **rendu** de l'écran de saisie du poste de cible — le premier de cet écran.
//
// CA d'E16US020 : « l'écran dit pourquoi le refus tombe — un refus muet serait pire que
// l'écrasement qu'il remplace ». ⚠️ **Monter l'écran, pas le message** : un test du seul
// `MessageErreurSaisie` resterait vert après l'avoir détaché du pavé — le défaut de `DETTE-085`,
// que `tsc` ne voit pas, une propriété calculée et jamais rendue ne cassant aucune compilation.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ErreurApi } from '../../shared/api/client'
import { Saisie } from './Saisie'

const LIGNE = {
  position: 'A',
  archer_id: 12,
  nom: 'DURAND',
  prenom: 'Léa',
  zones: ['10', '9', '8', 'M'],
  forfait: false,
}

const SERIE = { archer_id: 12, cumul: 0, volees: [], grain: null }

let erreurSaisie: Error | null = null

vi.mock('./hooks', () => ({
  useRejeuFileHorsLigne: () => undefined,
  useGrille: () => ({ data: [LIGNE], isError: false, isSuccess: true, error: null }),
  useBareme: () => ({ data: { nb_volees: 2, nb_fleches_par_volee: 3 } }),
  useGrain: () => ({ data: null }),
  useDeparts: () => ({ data: [], isSuccess: true }),
  useFixerDepart: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  useSerie: () => ({ data: SERIE, isError: false, isSuccess: true, error: null }),
  useSeries: () => [{ data: SERIE, isSuccess: true }],
  useSaisirVolee: () => ({
    // ⚠️ `mutate` **joue** le rappel d'échec : un `vi.fn()` nu prouvait que la chaîne est rendue,
    // jamais qu'elle est vraie — c'est ce qui avait laissé passer le pavé qui affiche encore la
    // frappe refusée sous « le score affiché fait foi » (relevé en revue).
    mutate: (_corps: unknown, options?: { onError?: (e: Error) => void }) => {
      if (erreurSaisie) options?.onError?.(erreurSaisie)
    },
    isPending: false,
    isError: erreurSaisie !== null,
    error: erreurSaisie,
  }),
}))

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(<Saisie tournoiId={1} cibleIndex={1} />, { wrapper: Enveloppe })
}

async function ouvrirLePave() {
  monter()
  // ⚠️ Par la liste : « DURAND » figure AUSSI dans le sélecteur de marqueur, qui dérive de la
  // grille — un `findByText` y trouverait deux nœuds.
  const grille = await screen.findByRole('list')
  await userEvent.click(within(grille).getByRole('button'))
}

describe('Saisie — un refus de préséance est expliqué', () => {
  // ⚠️ Sans cette remise à zéro, un cas qui oublierait d'affecter `erreurSaisie` hériterait
  // silencieusement de l'erreur du précédent et passerait pour la mauvaise raison : la suite
  // serait verte par ordre d'exécution, pas par construction.
  beforeEach(() => {
    erreurSaisie = null
  })

  it('dit QUI a écrit et QUEL est le recours', async () => {
    erreurSaisie = new ErreurApi(
      409,
      'ecriture_de_role_inferieur',
      "Cette volée a été saisie par l'organisateur : seul un rôle au moins équivalent peut la modifier.",
    )

    await ouvrirLePave()

    const alerte = await screen.findByRole('alert')
    expect(alerte).toHaveTextContent(/saisie par l’organisateur|saisie par l'organisateur/)
    expect(alerte).toHaveTextContent(/signalez l’erreur à l’organisateur/)
  })

  it('efface la frappe refusée : le pavé retombe sur la vérité du serveur', async () => {
    erreurSaisie = new ErreurApi(409, 'ecriture_de_role_inferieur', 'Saisie par l’organisateur.')

    const { container } = monter()
    const grille = await screen.findByRole('list')
    await userEvent.click(within(grille).getByRole('button'))
    for (let i = 0; i < 3; i += 1) {
      await userEvent.click(screen.getByRole('button', { name: '10' }))
    }
    expect(container.querySelector('.saisie__buffer')).toHaveTextContent('101010')

    await userEvent.click(screen.getByRole('button', { name: /Enregistrer la volée/ }))

    expect(container.querySelector('.saisie__buffer')).not.toHaveTextContent('10')
  })

  it('laisse les autres refus au message générique', async () => {
    // ⚠️ Sans ce jumeau, rendre le message de préséance pour TOUTE erreur passerait inaperçu :
    // le premier test resterait vert, et le marqueur lirait « signalez à l'organisateur » sur une
    // panne réseau ou un refus de cible.
    erreurSaisie = new ErreurApi(403, 'saisie_hors_cible', 'Archer hors de votre cible.')

    await ouvrirLePave()

    const alerte = await screen.findByRole('alert')
    expect(alerte).toHaveTextContent('Archer hors de votre cible.')
    expect(alerte).not.toHaveTextContent(/signalez/)
  })
})
