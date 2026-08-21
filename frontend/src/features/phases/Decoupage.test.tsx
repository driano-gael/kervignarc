// Le **découpage en tours** d'une qualification, sur l'écran des phases (E05US035, ADR-0093).
//
// ⚠️ **Ce fichier existe parce que la revue a montré qu'aucun test ne pouvait voir le défaut** —
// et c'est la seconde fois dans ce même dossier, après `BorneSuisse.test.tsx`, dont l'entête
// raconte exactement la même histoire.
//
// `decoupage.ts` était pur, testé, parfaitement vert. Pendant ce temps, `ReglageDecoupage` était
// monté dans `FormulairePhase` sous `{estQualification && …}` — une branche **morte** : la
// qualification n'ouvre jamais ce formulaire (`gereeAilleurs`) et n'est pas dans
// `TYPES_AJOUTABLES`. Le réglage central de l'US n'était donc atteignable par **aucun** écran de
// tournoi, et `nb_volees`, ajouté au serveur exprès pour l'alimenter, n'avait aucun lecteur.
//
// Un test de formatage ne voit pas un défaut de câblage ; seul un test qui monte **l'écran** le
// voit. C'est pourquoi celui-ci monte `Phases` en entier, et non le contrôle isolé : ce qu'on
// garde ici n'est pas « le composant sait afficher », c'est « l'organisateur peut l'atteindre ».

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import type { EtapeDeroule } from './api'
import { getPhases } from './api'
import { Phases } from './Phases'

vi.mock('./api', () => ({
  getPhases: vi.fn(),
  getAvancement: vi.fn(async () => []),
  ajouterPhase: vi.fn(),
  modifierPhase: vi.fn(),
  reordonnerPhases: vi.fn(),
  supprimerPhase: vi.fn(),
  changerStatutPhase: vi.fn(),
}))

const QUALIFICATION: EtapeDeroule = {
  id: 7,
  tournoi_id: 1,
  ordre: 1,
  type: 'qualification',
  sources: [],
  effectif: null,
  barrage_jusqu_au: null,
  profondeur: null,
  poules: null,
  big_shoot_off: null,
  suisse: null,
  decoupage: null,
  nb_volees: 20,
  arrets: [],
}

function monter(phase: EtapeDeroule) {
  vi.mocked(getPhases).mockResolvedValue([phase])
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<Phases tournoiId={1} />, { wrapper: Enveloppe })
}

describe('le découpage en tours sur l’écran des phases', () => {
  it('est atteignable sur une qualification, sans passer par un formulaire d’édition', async () => {
    // LE test du bloquant : la qualification est « gérée ailleurs », donc son réglage doit vivre
    // à côté de la carte, comme le barrage — et non dans un formulaire qu'elle n'ouvre jamais.
    monter(QUALIFICATION)

    expect(await screen.findByText(/Découpage en tours/)).toBeInTheDocument()
  })

  it('annonce ce que le découpage donne, sur le barème RÉEL du tournoi', async () => {
    // L'autre moitié : `nb_volees` vient du serveur (`EtapeReponse`). S'il n'arrivait pas, l'écran
    // afficherait « la longueur dépend du barème du tournoi qui appliquera ce format » — phrase de
    // l'atelier de bibliothèque, absurde ici — et tout resterait vert.
    monter({ ...QUALIFICATION, decoupage: { nb_tours: 2 } })

    expect(await screen.findByText(/2 tours de 10 volées/)).toBeInTheDocument()
  })

  it('nomme le refus à venir quand le découpage ne tombe pas juste', async () => {
    monter({ ...QUALIFICATION, decoupage: { nb_tours: 3 } })

    expect(
      await screen.findByText(/20 volées ne se découpent pas en 3 tours égaux/),
    ).toBeInTheDocument()
  })

  it('dit qu’aucune pause ne peut se poser tant que la qualification n’est pas découpée', async () => {
    // La phrase doit être vraie : c'est le pendant visible du refus serveur. Avant le correctif,
    // l'écran l'affichait tout en offrant, deux blocs plus bas, un formulaire de pause.
    monter(QUALIFICATION)

    expect(await screen.findByText(/La qualification se tire d’un seul bloc/)).toBeInTheDocument()
  })
})
