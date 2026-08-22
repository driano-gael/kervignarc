// La **borne d'effectif** d'une phase au système suisse, sur l'écran des phases (E05US030).
//
// ⚠️ **Ce fichier existe parce que la revue a montré qu'aucun test ne pouvait voir le défaut.**
// `decrireBorne` était pure, testée, et parfaitement verte pendant que l'écran ne lui donnait
// **aucun** effectif (`effectif={null}`) : la borne ne s'affichait donc nulle part, précisément sur
// le seul écran où « l'effectif du jour » du CA existe vraiment. Un test de formatage ne voit pas
// un défaut de câblage ; seul un test de rendu le voit.
//
// Le second cas garde l'autre moitié : la borne affichée est celle que le **serveur** a calculée
// (`rondes_maximales`), pas celle que le miroir TypeScript recalculerait. Les deux formules
// coïncident aujourd'hui — c'est bien pour ça qu'il faut l'asserter : le jour où elles divergeront,
// rien d'autre ne le dira.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { cleSuissePublique } from '../saisie-duels/hooks'
import type { EtatSuissePublique } from '../suisse/api'
import type { EtapeDeroule } from './api'
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

const PHASE: EtapeDeroule = {
  id: 7,
  tournoi_id: 1,
  ordre: 2,
  type: 'suisse',
  sources: [],
  effectif: null,
  barrage_jusqu_au: null,
  profondeur: null,
  poules: null,
  big_shoot_off: null,
  suisse: { nb_rondes: 5 },
  colline: null,
  decoupage: null,
  nb_volees: null,
  // E05US033 : les deux réglages neufs. `null` / `[]` = le comportement d'avant l'US.
  arrets: [],
}

/** Monte le formulaire avec l'état de la phase **déjà en cache** — c'est ce que fait l'écran réel,
 * qui lit cette même entrée pour son bouton de pose de plan. */
function poser(etat: Partial<EtatSuissePublique>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(cleSuissePublique(1, 7), {
    phase_id: 7,
    nb_rondes: 5,
    rondes_maximales: 3,
    effectif: 4,
    rondes: [],
    classement: [],
    conflits: [],
    ...etat,
  })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<FormulairePhase tournoiId={1} phases={[PHASE]} phase={PHASE} />, { wrapper: Enveloppe })
}

describe('la borne d’effectif sur l’écran des phases', () => {
  it('annonce la borne sur l’effectif RÉEL du créneau', async () => {
    // Le CA : « le maximum que l'effectif du jour autorise, affiché en clair ». Avant le correctif,
    // cet écran passait `null` et n'affichait rien du tout.
    poser({})

    expect(
      await screen.findByText(/4 archers : 3 rondes au maximum sans que deux archers/),
    ).toBeInTheDocument()
  })

  it('nomme l’écart quand le réglage dépasse ce que l’effectif permet', async () => {
    // C'est la moitié qui coûte : le serveur **borne à la lecture** sans rien lever, donc sans
    // cette phrase l'organisateur croit jouer 5 rondes et en voit 3 le jour J.
    poser({})

    expect(
      await screen.findByText(/Vous en avez réglé 5 : les 3 premières seront jouées/),
    ).toBeInTheDocument()
  })

  it('affiche la borne DU SERVEUR, et non celle que le miroir recalculerait', async () => {
    // Sonde : un `rondes_maximales` volontairement incohérent avec l'effectif. Le miroir
    // (`rondesMaximales(4)`) dirait 3 ; l'autorité dit 2, et c'est elle qui doit s'afficher.
    poser({ rondes_maximales: 2 })

    expect(await screen.findByText(/4 archers : 2 rondes au maximum/)).toBeInTheDocument()
    expect(screen.queryByText(/3 rondes au maximum/)).toBeNull()
  })
})
