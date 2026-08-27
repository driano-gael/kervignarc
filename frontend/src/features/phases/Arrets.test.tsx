// Les **pauses programmées** sur les phases d'un tournoi réel (E05US033, ADR-0091).
//
// ⚠️ **Troisième fois que le même défaut est signalé sur ce formulaire** : `Profondeur.test.tsx` a
// été écrit pour le premier (E06US006), la note de `api.ts` raconte le second (`barrage_jusqu_au`).
// L'édition d'une phase est un `PUT` **total** : un champ non réémis est **effacé**,
// silencieusement, par une requête qui réussit — et un planning de pauses est une liste saisie
// ligne à ligne, dont l'absence ne se voit que le jour J. On double les **appels HTTP** seulement.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { modifierPhase, type ConfigPhase, type EtapeDeroule } from './api'
import { FormulairePhase } from './Phases'

vi.mock('./api', () => ({
  getPhases: vi.fn(),
  getAvancement: vi.fn(),
  ajouterPhase: vi.fn(),
  modifierPhase: vi.fn(),
  reordonnerPhases: vi.fn(),
  supprimerPhase: vi.fn(),
  changerStatutPhase: vi.fn(),
}))

// Une étape au **système suisse** : un des quatre types qui annoncent leurs tours, donc un des
// quatre sur lesquels une pause peut se poser.
const PHASE: EtapeDeroule = {
  id: 7,
  tournoi_id: 1,
  ordre: 2,
  type: 'suisse',
  sources: [],
  effectif: 16,
  barrage_jusqu_au: null,
  profondeur: null,
  poules: null,
  big_shoot_off: null,
  suisse: { nb_rondes: 5 },
  colline: null,
  decoupage: null,
  titre: null,
  nb_volees: null,
  arrets: [
    { apres_tour: 2, portee: 'phase' },
    { apres_tour: 4, portee: 'depart' },
  ],
}

function poser(phase: EtapeDeroule = PHASE) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<FormulairePhase tournoiId={1} phases={[phase]} phase={phase} />, { wrapper: Enveloppe })
}

const configEnvoyee = (): ConfigPhase =>
  (vi.mocked(modifierPhase).mock.calls[0] as [number, number, ConfigPhase])[2]

/**
 * Le **dernier** champ « Après le tour » — celui de la ligne qu'on vient d'ajouter.
 *
 * Le `throw` n'est pas décoratif : `noUncheckedIndexedAccess` fait rendre `HTMLElement | undefined` à
 * un accès par index, et une assertion non nulle (`!`) masquerait le vrai cas d'échec — « le bouton
 * *Ajouter une pause* n'a rien ajouté ». Ici, ce cas produit un message qui le dit.
 */
function dernierChampDeTour(): HTMLElement {
  const champs = screen.getAllByLabelText(/Après le tour/)
  const dernier = champs.at(-1)
  if (!dernier) throw new Error('aucun champ « Après le tour » à l’écran')
  return dernier
}

describe('les pauses programmées sur les phases d’un tournoi', () => {
  // ⚠️ **Sans ce reset, `configEnvoyee()` lit l'appel d'un test PRÉCÉDENT** : le mock de module est
  // partagé par tout le fichier, donc `mock.calls[0]` n'est le bon appel que pour le premier test
  // qui soumet. Deux tests d'affilée passaient en isolation et échouaient ensemble.
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le planning que porte la phase', () => {
    poser()

    const champs = screen.getAllByLabelText(/Après le tour/)
    expect(champs.map((champ) => (champ as HTMLInputElement).value)).toEqual(['2', '4'])
    const portees = screen.getAllByLabelText(/Portée/)
    expect(portees.map((champ) => (champ as HTMLSelectElement).value)).toEqual(['phase', 'depart'])
  })

  it('réémet le planning entier quand on ne corrige que l’effectif', async () => {
    vi.mocked(modifierPhase).mockResolvedValue(PHASE)
    poser()

    const effectif = screen.getByLabelText(/Effectif/)
    await userEvent.clear(effectif)
    await userEvent.type(effectif, '8')
    await userEvent.click(screen.getByRole('button', { name: /Enregistrer|Valider/ }))

    await waitFor(() => expect(modifierPhase).toHaveBeenCalled())
    // ⚠️ Le point du fichier : corriger un détail ne doit pas effacer le planning de journée.
    expect(configEnvoyee().arrets).toEqual([
      { apres_tour: 2, portee: 'phase' },
      { apres_tour: 4, portee: 'depart' },
    ])
  })

  it('ajoute une pause et l’envoie', async () => {
    vi.mocked(modifierPhase).mockResolvedValue(PHASE)
    poser()

    await userEvent.click(screen.getByRole('button', { name: /Ajouter une pause/ }))
    await userEvent.type(dernierChampDeTour(), '5')
    await userEvent.click(screen.getByRole('button', { name: /Enregistrer|Valider/ }))

    await waitFor(() => expect(modifierPhase).toHaveBeenCalled())
    expect(configEnvoyee().arrets).toHaveLength(3)
  })

  it('bloque la soumission et dit pourquoi quand deux pauses visent le même tour', async () => {
    poser()

    await userEvent.click(screen.getByRole('button', { name: /Ajouter une pause/ }))
    await userEvent.type(dernierChampDeTour(), '2')

    // L'invariant que `Profondeur.test.tsx` garde aussi : bouton bloqué ⟺ un message dit pourquoi.
    expect(screen.getByRole('button', { name: /Enregistrer|Valider/ })).toBeDisabled()
    // ⚠️ `getAllByRole` et non `getByRole` : depuis le correctif de revue d'E05US027, la **borne
    // d'effectif** du système suisse s'affiche elle aussi en `role="status"` dès qu'un effectif est
    // déclaré — ce que le CA demande et qui n'arrivait pas jusque-là. Deux messages de statut
    // cohabitent donc légitimement ; on cible celui qu'on teste.
    expect(
      screen
        .getAllByRole('status')
        .map((noeud) => noeud.textContent)
        .join(' '),
    ).toMatch(/même tour/)
  })

  it('refuse le réglage sur un type qui n’annonce pas ses tours, et dit où les pauses se posent', async () => {
    // ⚠️ **Le témoin est passé de `colline` à `barrage` en E05US027** : la colline est devenue
    // arrêtable (son service sait dire où elle en est, ADR-0093), donc elle ne pouvait plus servir
    // d'exemple. Le `barrage` est un porteur **durable** — c'est un départage, pas un format qu'on
    // déroule, et il n'a aucun tour à observer par nature.
    poser()

    await userEvent.selectOptions(screen.getByLabelText(/Type de la phase/), 'barrage')

    // Aucun champ offert — le serveur refuserait l'arrêt (422) et, le `PUT` étant total, c'est
    // l'étape entière qui serait recalée.
    expect(screen.queryAllByLabelText(/Après le tour/)).toEqual([])
    expect(screen.queryByRole('button', { name: /Ajouter une pause/ })).toBeNull()
    // Mais le motif est écrit : cacher la fiche laisserait chercher un réglage vu sur la phase
    // voisine sans jamais apprendre qu'il n'existe pas ici.
    expect(screen.getByText(/n’annonce pas ses tours/)).toBeInTheDocument()
  })

  it('n’envoie aucune pause sur un type non arrêtable, même si l’écran en portait', async () => {
    vi.mocked(modifierPhase).mockResolvedValue(PHASE)
    poser()

    await userEvent.selectOptions(screen.getByLabelText(/Type de la phase/), 'barrage')
    await userEvent.click(screen.getByRole('button', { name: /Enregistrer|Valider/ }))

    await waitFor(() => expect(modifierPhase).toHaveBeenCalled())
    // ⚠️ **Perte de planning assumée** : conserver les arrêts ferait échouer l'enregistrement entier
    // avec un message que l'écran ne sait pas rattacher au bon champ — l'organisateur ne pourrait
    // plus enregistrer du tout. C'est la même garde que les quatre réglages voisins.
    expect(configEnvoyee().arrets).toEqual([])
  })
})
