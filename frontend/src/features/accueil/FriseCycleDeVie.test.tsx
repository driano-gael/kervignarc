// Tests de l'**avertissement d'effectif** de la frise (E05US021).
//
// Le CA « visible avant le clic » est la promesse centrale de l'US — `docs/fonctionnel/E05US021.md`
// l'appelle « l'étape la plus importante de la fiche ». Elle était livrée sans aucun test front.
//
// Trois comportements non triviaux se jouent ici, et chacun a un mode de défaillance silencieux :
//  - l'encart ne doit apparaître **qu'avant le lancement** (le rappeler sur un tournoi en cours
//    serait un reproche sans action possible — et la fiche liste ce cas comme un défaut) ;
//  - la **cause** se lit sur `origine`, jamais sur `ordre_phase === null` : c'est le défaut relevé
//    en revue, où le produit annonçait une règle de club là où il n'y en avait aucune ;
//  - une lecture en échec ne doit **rien** afficher : l'avertissement est un confort, il ne doit pas
//    transformer un hoquet réseau en alarme.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { StatutTournoi, Tournoi } from '../competition/api'
import { getExigenceEffectif, getTransitions, type ExigenceEffectif } from './api'
import { FriseCycleDeVie } from './FriseCycleDeVie'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getTransitions: vi.fn(),
  getExigenceEffectif: vi.fn(),
  transitionnerTournoi: vi.fn(),
}))

function tournoi(statut: StatutTournoi): Tournoi {
  return {
    id: 1,
    nom: 'Trophée',
    date: '2026-03-14',
    lieu: null,
    type_tournoi: 'non_officiel',
    statut,
  } as Tournoi
}

function exigence(partiel: Partial<ExigenceEffectif> = {}): ExigenceEffectif {
  return {
    inscrits: 28,
    minimum: 34,
    suffisant: false,
    origine: 'deroule',
    ordre_phase: 3,
    rang_debut: 33,
    ...partiel,
  }
}

function enveloppe() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

/** Monte la frise et rend l'encart **une fois affiché** — pour les cas de présence. */
async function encartDe(statut: StatutTournoi) {
  render(<FriseCycleDeVie tournoi={tournoi(statut)} />, { wrapper: enveloppe() })
  return screen.findByRole('status')
}

/** Monte la frise et vérifie qu'**aucun** encart n'apparaît — pour les cas d'absence.
 *
 * ⚠️ Deux pièges, et les deux ont été rencontrés. Attendre un élément toujours présent (la frise
 * elle-même) rend la main **avant** la query : « pas d'encart » serait vrai par construction, et le
 * test ne prouverait rien. Mais attendre la query puis vider les microtâches ne suffit pas non
 * plus — sous charge, le re-rendu peut arriver après, ce qui rendait le test **instable** en suite
 * complète. On laisse donc `waitFor` retenter jusqu'à ce que la query soit *settled*, puis on
 * conclut : à ce stade, un encart dû serait monté.
 */
async function pasDEncart(statut: StatutTournoi) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<FriseCycleDeVie tournoi={tournoi(statut)} />, {
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  })
  await waitFor(() =>
    expect(client.getQueryState(['exigence-effectif', 1])?.fetchStatus).toBe('idle'),
  )
  return screen.queryByRole('status')
}

describe('AvertissementEffectif', () => {
  beforeEach(() => {
    vi.mocked(getTransitions).mockResolvedValue([])
    vi.mocked(getExigenceEffectif).mockResolvedValue(exigence())
  })

  it('chiffre le manque et nomme la phase en cause sur un tournoi prêt', async () => {
    render(<FriseCycleDeVie tournoi={tournoi('pret')} />, { wrapper: enveloppe() })

    const encart = await screen.findByRole('status')
    // `D-16`/`P-4` : l'alerte chiffre son impact — les deux nombres, pas seulement « trop peu ».
    expect(encart.textContent).toContain('28')
    expect(encart.textContent).toContain('34')
    expect(encart.textContent).toContain('phase 3')
    expect(encart.textContent).toContain('33')
    // `DV-03` : jamais la couleur seule.
    expect(encart.textContent).toContain('Effectif insuffisant')
    expect(encart.className).toContain('carte__etat--alerte')
  })

  it.each<StatutTournoi>(['brouillon', 'pret'])(
    'prévient tant que le tournoi n’est pas lancé (%s)',
    async (statut) => {
      expect(await encartDe(statut)).not.toBeNull()
    },
  )

  it.each<StatutTournoi>(['en_cours', 'en_pause', 'termine', 'archive', 'annule'])(
    'ne dit plus rien une fois le tournoi lancé ou clos (%s)',
    async (statut) => {
      // Le rappeler après le départ serait un reproche sans action possible.
      // ⚠️ Les 7 statuts sont exercés, pas seulement `pret`/`en_cours` : réduire la condition à
      // `statut === 'pret'` laissait les tests verts en cassant le CA pour un **brouillon** —
      // l'état où l'organisateur passe le plus de temps.
      expect(await pasDEncart(statut)).toBeNull()
    },
  )

  it('se tait quand le compte y est', async () => {
    vi.mocked(getExigenceEffectif).mockResolvedValue(exigence({ inscrits: 40, suffisant: true }))

    expect(await pasDEncart('pret')).toBeNull()
  })

  it('n’invente pas de règle de club quand le minimum vient du déroulé', async () => {
    // Cas du format nominal (qualification seule) : aucun prélèvement en cause, donc pas de phase
    // à nommer — mais surtout, pas de « ce format exige » alors que personne n'a rien exigé.
    vi.mocked(getExigenceEffectif).mockResolvedValue(
      exigence({ inscrits: 0, minimum: 1, ordre_phase: null, rang_debut: null }),
    )

    const encart = await encartDe('pret')
    expect(encart.textContent).toContain('déroulé')
    expect(encart.textContent).not.toContain('exige')
  })

  it('annonce la règle de club quand c’est elle qui commande', async () => {
    vi.mocked(getExigenceEffectif).mockResolvedValue(
      exigence({ inscrits: 36, minimum: 40, origine: 'club', ordre_phase: null, rang_debut: null }),
    )

    const encart = await encartDe('pret')
    expect(encart.textContent).toContain('exige')
    expect(encart.textContent).toContain('40')
    expect(encart.textContent).not.toContain('phase')
  })

  it('n’affiche rien si la lecture échoue', async () => {
    // Un hoquet réseau ne doit pas se transformer en alarme sur un tournoi peut-être complet.
    vi.mocked(getExigenceEffectif).mockRejectedValue(new Error('injoignable'))

    expect(await pasDEncart('pret')).toBeNull()
  })
})
