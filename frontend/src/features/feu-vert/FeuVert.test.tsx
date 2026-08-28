// Tests de **rendu** du feu vert (E16US008) — la surface que `etat.test.ts` ne voit pas.
//
// ⚠️ `etat.test.ts` teste des fonctions **pures** : il ignore ce que le composant en fait. Trois
// comportements à défaillance silencieuse vivent uniquement ici — la portée `'admin'` de la
// déclaration (un 6ᵉ argument optionnel qui, s'il saute, fait partir la requête sans identité →
// 401 le jour J, sans qu'aucune porte ne rougisse), l'absence de bouton sur un duel amont à demi
// connu (le forfait y serait écrit sans rien débloquer), et le renvoi au plan de duels.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { declarerForfaitDuel } from '../forfaits/api'
import type { DuelAVenir, FeuVert as FeuVertData, ResumeLancement } from './api'
import { FeuVert } from './FeuVert'
import { useFeuVert, useImpactLancement } from './hooks'

vi.mock('../forfaits/api', () => ({ declarerForfaitDuel: vi.fn() }))
vi.mock('../departs/hooks', () => ({
  useCreneauDesDuels: () => ({
    departs: { data: [] },
    liste: [],
    departId: 1,
    choisir: vi.fn(),
  }),
}))
vi.mock('../phases/hooks', () => ({
  useAvancementPhases: () => ({
    data: [{ id: 7, type: 'elimination_directe', libelle: 'Tableau' }],
    isPending: false,
  }),
}))
vi.mock('./hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./hooks')>()),
  useFeuVert: vi.fn(),
  useImpactLancement: vi.fn(),
}))

function duel(patch: Partial<DuelAVenir>): DuelAVenir {
  return {
    numero: 1,
    tour: 1,
    haut: { archer_id: 1, nom: 'Hood', prenom: 'Robin' },
    bas: { archer_id: 2, nom: 'Scarlet', prenom: 'Will' },
    participants_connus: true,
    cible_haut: 4,
    cible_bas: 4,
    cible_attribuee: true,
    sources_en_attente: [],
    pret_a_lancer: true,
    blocage: null,
    ...patch,
  }
}

function monter(duels: DuelAVenir[], surPlanDeDuels = vi.fn()) {
  const donnees: FeuVertData = {
    phase_id: 7,
    est_termine: false,
    duels,
    nb_prets: duels.filter((d) => d.pret_a_lancer).length,
  }
  vi.mocked(useFeuVert).mockReturnValue({ data: donnees, isPending: false } as ReturnType<
    typeof useFeuVert
  >)
  const impact: ResumeLancement = {
    phase_id: 7,
    numeros: duels.filter((d) => d.pret_a_lancer).map((d) => d.numero),
    cibles: [],
    nb_duels: duels.filter((d) => d.pret_a_lancer).length,
    nb_archers: 0,
  }
  vi.mocked(useImpactLancement).mockReturnValue({ data: impact, isPending: false } as ReturnType<
    typeof useImpactLancement
  >)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  render(<FeuVert tournoiId={1} surPlanDeDuels={surPlanDeDuels} />, { wrapper: Wrapper })
  return { surPlanDeDuels }
}

describe('FeuVert — actions sur la ligne bloquée', () => {
  beforeEach(() => {
    vi.mocked(declarerForfaitDuel).mockReset()
    vi.mocked(declarerForfaitDuel).mockResolvedValue({
      declare_par: 'Administrateur',
    } as Awaited<ReturnType<typeof declarerForfaitDuel>>)
  })

  it('déclare le forfait en portée admin — pas en scoreur', async () => {
    const amont = duel({ numero: 3, tour: 1 })
    const aval = duel({
      numero: 9,
      tour: 2,
      pret_a_lancer: false,
      participants_connus: false,
      haut: null,
      bas: null,
      cible_attribuee: false,
      sources_en_attente: [3],
      blocage: 'en attente du duel n°3',
    })
    monter([amont, aval])

    await userEvent.click(await screen.findByRole('button', { name: /Voir le duel qui bloque/ }))
    await userEvent.click(screen.getByRole('button', { name: /Déclarer Robin Hood forfait/ }))
    // ⚠️ DETTE-090 : le dialogue AVERTIT de l'irréversibilité au lieu de promettre le contraire.
    // C'est le seul garde-fou de cette dette — sans cette assertion, la promesse peut repousser.
    expect(screen.getAllByText(/Aucun écran ne défait un forfait de duel/)).toHaveLength(2)
    await userEvent.click(screen.getByRole('button', { name: 'Déclarer forfait' }))

    await waitFor(() => expect(declarerForfaitDuel).toHaveBeenCalledTimes(1))
    // ⚠️ L'assertion qui compte : la **portée**. Sans elle, aucun jeton n'est joint depuis l'écran
    // d'administration et tout forfait part anonyme.
    expect(vi.mocked(declarerForfaitDuel).mock.calls[0]).toEqual([
      1,
      7,
      1,
      'abandon',
      undefined,
      'admin',
    ])
  })

  it('n’offre aucun forfait quand le duel amont n’a qu’un camp connu', async () => {
    const amont = duel({
      numero: 3,
      tour: 1,
      bas: null,
      participants_connus: false,
      pret_a_lancer: false,
    })
    const aval = duel({
      numero: 9,
      tour: 2,
      pret_a_lancer: false,
      participants_connus: false,
      haut: null,
      bas: null,
      cible_attribuee: false,
      sources_en_attente: [3],
      blocage: 'en attente du duel n°3',
    })
    monter([amont, aval])

    await userEvent.click(await screen.findByRole('button', { name: /Voir le duel qui bloque/ }))
    // Le dépliage dit ce qu'il sait (le camp connu, la cible) ; seul le forfait est refusé.
    // ⚠️ On cible la liste dépliée : la LIGNE du duel amont affiche le même texte, et c'est voulu
    // — les deux vues du même duel doivent concorder.
    // ⚠️ `toBeVisible`, pas `toBeInTheDocument` : le `<ul>` est monté même replié (`hidden`), pour
    // que `aria-controls` ne pointe pas dans le vide. Sans la visibilité, ces lignes passeraient
    // SANS le clic ci-dessus — le seul test du dépliage ne prouverait plus rien.
    const liste = document.getElementById('feu-vert-sources-9') as HTMLElement
    expect(liste).toBeVisible()
    expect(within(liste).getByText(/Robin Hood vs —/)).toBeVisible()
    expect(screen.queryByRole('button', { name: /forfait/i })).not.toBeInTheDocument()
  })

  it('nomme les DEUX duels qui bloquent et compte ce qui reste attendu', async () => {
    // ⚠️ Le cas nominal, et il n'était couvert par rien : un duel de tableau attend TOUJOURS deux
    // sources (`construire_tableau` engendre chaque match de tour n+1 depuis deux matchs). Le
    // libellé pluriel et le complément « Elle attend encore N autre duel. » ne vivent que là.
    const amontA = duel({ numero: 3, tour: 1 })
    const amontB = duel({
      numero: 4,
      tour: 1,
      haut: { archer_id: 5, nom: 'Tuck', prenom: 'Frère' },
      bas: { archer_id: 6, nom: 'Little', prenom: 'John' },
    })
    const aval = duel({
      numero: 9,
      tour: 2,
      pret_a_lancer: false,
      participants_connus: false,
      haut: null,
      bas: null,
      cible_attribuee: false,
      sources_en_attente: [3, 4],
      blocage: 'en attente du duel n°3, n°4',
    })
    monter([amontA, amontB, aval])

    await userEvent.click(
      await screen.findByRole('button', { name: /Voir les duels qui bloquent/ }),
    )
    const liste = document.getElementById('feu-vert-sources-9') as HTMLElement
    expect(within(liste).getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: /forfait$/ })).toHaveLength(4)
    expect(screen.getAllByText(/Elle attend encore 1 autre duel\./).length).toBeGreaterThan(0)
  })

  it('renvoie au plan de duels quand la cible manque au tour 1', async () => {
    const sans_cible = duel({
      numero: 2,
      tour: 1,
      pret_a_lancer: false,
      cible_attribuee: false,
      cible_haut: null,
      cible_bas: null,
      blocage: 'cible non attribuée',
    })
    const { surPlanDeDuels } = monter([sans_cible])

    await userEvent.click(
      await screen.findByRole('button', { name: /Attribuer une cible — ouvrir le plan de duels/ }),
    )
    expect(surPlanDeDuels).toHaveBeenCalledTimes(1)
  })
})
