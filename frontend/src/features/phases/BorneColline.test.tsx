// La **borne de portée** d'une phase de colline, sur l'écran des phases (E05US027).
//
// ⚠️ **Jumeau de `BorneSuisse.test.tsx`, pour la même raison** : `decrireBorne` était pure, testée
// et verte pendant que l'écran ne lui passait **aucun** effectif — un test de formatage ne voit pas
// un défaut de câblage. ⚠️ Le troisième cas garde une moitié propre à cet écran : la borne annoncée
// doit être celle que le serveur **oppose**, donc celle de l'effectif **déclaré** dans le
// formulaire, pas celle de la population déjà prélevée. Sinon : feu vert à l'écran, 422 à
// l'enregistrement.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import type { EtatCollinePublique } from '../colline/api'
import { cleCollinePublique } from '../saisie-duels/hooks'
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
  type: 'colline',
  sources: [],
  effectif: null,
  barrage_jusqu_au: null,
  profondeur: null,
  poules: null,
  big_shoot_off: null,
  suisse: null,
  // Un Ladder réglé au-delà de ce que 8 archers permettent : c'est le cas qui doit *parler*.
  colline: { nb_manches: 3, portee_de_defi: 12 },
  decoupage: null,
  titre: null,
  nb_volees: null,
  arrets: [],
}

/** Monte le formulaire avec l'état de la phase **déjà en cache** — c'est ce que fait l'écran réel,
 * qui lit cette même entrée pour son bouton de pose de plan. */
function poser(etat: Partial<EtatCollinePublique> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(cleCollinePublique(1, 7), {
    phase_id: 7,
    nb_manches: 3,
    portee_de_defi: 12,
    portee_maximale: 7,
    effectif: 8,
    manches: [],
    classement: [],
    conflits: [],
    ...etat,
  })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<FormulairePhase tournoiId={1} phases={[PHASE]} phase={PHASE} />, { wrapper: Enveloppe })
}

describe('la borne de portée sur l’écran des phases', () => {
  it('annonce la borne sur l’effectif RÉEL du créneau', async () => {
    // Le CA : « la portée maximale que l'effectif autorise, affichée en clair ».
    poser()

    expect(
      await screen.findByText(/8 archers : un défi porte au plus sur 7 rangs/),
    ).toBeInTheDocument()
  })

  it('nomme l’écart quand le réglage dépasse ce que l’effectif permet', async () => {
    // La moitié qui coûte : le serveur **borne à la lecture** sans rien lever. Sans cette phrase,
    // l'organisateur croit jouer une portée de 12 et voit des défis bien plus courts le jour J.
    poser()

    expect(
      await screen.findByText(/Vous avez réglé 12 : 7 rangs seront appliqués/),
    ).toBeInTheDocument()
  })

  it('affiche la borne DU SERVEUR, et non celle que le miroir recalculerait', async () => {
    // Sonde : un `portee_maximale` volontairement incohérent avec l'effectif. Le miroir
    // (`porteeMaximale(8)`) dirait 7 ; l'autorité dit 2, et c'est elle qui doit s'afficher.
    poser({ portee_maximale: 2 })

    expect(
      await screen.findByText(/8 archers : un défi porte au plus sur 2 rangs/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/au plus sur 7 rangs/)).toBeNull()
  })

  it('bascule sur l’effectif DÉCLARÉ dès qu’on en saisit un — c’est lui que le serveur oppose', async () => {
    // ⚠️ Le cas du correctif de revue. `_verifier_portee_de_defi` refuse l'étape contre
    // `self.effectif`, le champ saisi ici même — pas contre la population prélevée. Annoncer la
    // borne des 8 prélevés pendant qu'on déclare une phase à 4 donne un feu vert suivi d'un 422.
    poser()
    await screen.findByText(/8 archers/)

    await userEvent.type(screen.getByLabelText(/Effectif/i), '4')

    expect(
      await screen.findByText(/4 archers : un défi porte au plus sur 3 rangs/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/8 archers/)).toBeNull()
  })

  it('annonce un REFUS et éteint le bouton, au lieu de promettre un raccourcissement', async () => {
    // ⚠️ **Le cas que la 1ʳᵉ version de ce fichier ne voyait pas** (relevé en 2ᵉ passe, axe C1) :
    // elle n'assertait que la première phrase, jamais la seconde ni l'état du bouton. Or le premier
    // correctif avait **inversé les deux régimes** — avec un effectif déclaré, il annonçait
    // « 3 rangs seront appliqués » alors que `_verifier_portee_de_defi` **lève** un 422. Le feu vert
    // avait changé de place, il ne s'était pas éteint.
    poser()
    await screen.findByText(/8 archers/)

    await userEvent.type(screen.getByLabelText(/Effectif/i), '4')

    expect(await screen.findByText(/l’enregistrement sera refusé/)).toBeInTheDocument()
    expect(screen.queryByText(/seront appliqués/)).toBeNull()
    // La moitié qui compte vraiment : le geste doit être **impossible**, pas seulement déconseillé.
    expect(screen.getByRole('button', { name: /Enregistrer|Valider/ })).toBeDisabled()
  })
})
