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
    tour_pose: 1,
    est_termine: false,
    duels,
    nb_prets: duels.filter((d) => d.pret_a_lancer).length,
  }
  // ⚠️ `mockImplementation` et non `mockReturnValue` : le feu vert doit pouvoir CHANGER entre deux
  // rendus. Sur une donnée figée, la ligne ne bascule jamais de `sources` vers `sans-recours` — or
  // c'est cette bascule seule qui motive le hissage de `retourDuGeste` hors des sorties anticipées.
  // Avec un mock constant, remettre le message dans la branche `sources` laisserait le test vert.
  vi.mocked(useFeuVert).mockImplementation(
    () => ({ data: donnees, isPending: false }) as ReturnType<typeof useFeuVert>,
  )
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
  const { rerender } = render(<FeuVert tournoiId={1} surPlanDeDuels={surPlanDeDuels} />, {
    wrapper: Wrapper,
  })
  // `rafraichir` rejoue ce que fait le poll de 5 s : `FeuVert` relit le feu vert et ses lignes
  // changent de branche. Sans cela seul `ActionLevee` se re-rend (son état de mutation), et la
  // bascule `sources` → `sans-recours` — la seule qui motive le hissage — reste invisible.
  const rafraichir = () => rerender(<FeuVert tournoiId={1} surPlanDeDuels={surPlanDeDuels} />)
  return { surPlanDeDuels, donnees, rafraichir }
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
    const { donnees, rafraichir } = monter([amont, aval])
    // ⚠️ Au succès, la ligne perd sa dernière source et bascule sur `sans-recours` — c'est l'état
    // que l'organisateur observe, et la raison d'être du hissage de `retourDuGeste`.
    vi.mocked(declarerForfaitDuel).mockImplementation(async () => {
      donnees.duels = [
        amont,
        duel({
          numero: 9,
          tour: 2,
          pret_a_lancer: false,
          participants_connus: true,
          cible_attribuee: false,
          cible_haut: null,
          cible_bas: null,
          sources_en_attente: [],
          blocage: 'cible non attribuée',
        }),
      ]
      return { declare_par: 'Administrateur' } as Awaited<ReturnType<typeof declarerForfaitDuel>>
    })

    await userEvent.click(await screen.findByRole('button', { name: /Voir le duel qui bloque/ }))
    await userEvent.click(screen.getByRole('button', { name: /Déclarer Robin Hood forfait/ }))
    // ⚠️ DETTE-090 : le dialogue AVERTIT de l'irréversibilité au lieu de promettre le contraire.
    // C'est le seul garde-fou de cette dette — sans cette assertion, la promesse peut repousser.
    expect(screen.getAllByText(/Aucun écran ne défait un forfait de duel/)).toHaveLength(2)
    await userEvent.click(screen.getByRole('button', { name: 'Déclarer forfait' }))

    await waitFor(() => expect(declarerForfaitDuel).toHaveBeenCalledTimes(1))
    // ⚠️ L'assertion qui compte : la **portée**. Sans elle, aucun jeton n'est joint depuis l'écran
    // d'administration et tout forfait part anonyme.
    // ⚠️ Les DEUX assertions ensemble, sinon rien n'est prouvé : la phrase grise atteste qu'on est
    // passé de l'autre côté du `return` anticipé de `sans-recours`, et le `status` que le retour du
    // geste y a survécu. Défaut livré en 2ᵉ passe, corrigé en 3ᵉ, gardé seulement maintenant.
    expect(await screen.findByRole('status')).toHaveTextContent(/Forfait enregistré/)
    rafraichir()
    expect(screen.getByText(/Les cibles de ce tour seront posées/)).toBeVisible()
    expect(screen.getByRole('status')).toHaveTextContent(/Forfait enregistré/)
    expect(screen.getByRole('status')).toHaveTextContent(/Forfait enregistré/)
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
    // ⚠️ Amont au tour 2 SANS cible, aval au tour 3 : un match de tour 1 à camp vide est un bye
    // (exclu des duels à venir), et `place = match.tour == 1` interdit toute cible au-delà — l'état
    // « un camp connu AVEC cible » n'existe pas côté serveur (cf. `etat.test.ts`).
    const amont = duel({
      numero: 3,
      tour: 2,
      bas: null,
      participants_connus: false,
      pret_a_lancer: false,
      cible_haut: null,
      cible_bas: null,
    })
    const aval = duel({
      numero: 9,
      tour: 3,
      pret_a_lancer: false,
      participants_connus: false,
      haut: null,
      bas: null,
      cible_attribuee: false,
      sources_en_attente: [3],
      blocage: 'en attente du duel n°3',
    })
    monter([amont, aval])

    // ⚠️ Deux lignes portent désormais ce bouton (l'amont attend lui aussi un duel) : on cible la
    // ligne aval par son `aria-controls`, sans quoi `findByRole` lève « multiple elements ».
    await screen.findAllByRole('button', { name: /Voir le duel qui bloque/ })
    const deplieur = document.querySelector<HTMLButtonElement>(
      '[aria-controls="feu-vert-sources-9"]',
    )
    expect(deplieur).not.toBeNull()
    await userEvent.click(deplieur as HTMLButtonElement)
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
    // ⚠️ Le régime « deux sources », qui n'était couvert par rien. Une ligne peut n'en attendre
    // qu'UNE (bye, ou duel amont déjà tranché) — oracle du régime :
    // `test_une_ligne_bloquee_attend_une_ou_deux_sources_selon_ce_qui_reste_a_trancher` (backend).
    // Ici, seuls le libellé pluriel et « Elle attend encore N autre duel. ».
    const amontA = duel({ numero: 3, tour: 1 })
    const amontB = duel({
      numero: 4,
      tour: 1,
      haut: { archer_id: 5, nom: 'Tuck', prenom: 'Frère' },
      bas: { archer_id: 6, nom: 'Little', prenom: 'John' },
      cible_haut: 7,
      cible_bas: 7,
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
    // Un `<dialog>` par bouton de forfait, monté en permanence : le compte est déterminé.
    expect(screen.getAllByText(/Elle attend encore 1 autre duel\./)).toHaveLength(4)
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
