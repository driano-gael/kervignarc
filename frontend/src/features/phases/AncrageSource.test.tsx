// L'**ancre d'un prélèvement** postée par l'écran des phases (E05US022, ADR-0078).
//
// ⚠️ **La ligne la plus risquée de l'US, que la revue a réclamé de couvrir.** Le `<select>` de
// phase source portait `value={p.ordre}` ; il porte désormais `value={p.id}`. Resté sur le rang,
// le serveur aurait **accepté** la requête sur tout tournoi dont les identités recouvrent les
// rangs — le cas d'un tournoi neuf — et le prélèvement aurait désigné une autre étape, sans
// erreur. Le décor donne donc aux étapes des identités **distinctes des rangs** (101, 102) :
// sinon le test passerait avec l'ancien code. Même discipline qu'`identite_d_etape` au backend.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ConfigPhase, EtapeDeroule } from './api'
import { ajouterPhase, getPhases } from './api'
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

const BASE: EtapeDeroule = {
  id: 101,
  tournoi_id: 1,
  ordre: 1,
  type: 'elimination_directe',
  sources: [],
  effectif: 32,
  barrage_jusqu_au: null,
  profondeur: null,
  poules: null,
  big_shoot_off: null,
  suisse: null,
  colline: null,
  decoupage: null,
  nb_volees: null,
  arrets: [],
  titre: null,
}

// ⚠️ Identités **décalées des rangs** : 101 pour le rang 1, 102 pour le rang 2.
const AMONT: EtapeDeroule = { ...BASE, id: 101, ordre: 1 }
const SECONDE: EtapeDeroule = { ...BASE, id: 102, ordre: 2, type: 'placement' }

beforeEach(() => {
  vi.mocked(ajouterPhase).mockClear()
})

function monter(phases: EtapeDeroule[]) {
  vi.mocked(getPhases).mockResolvedValue(phases)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<Phases tournoiId={1} />, { wrapper: Enveloppe })
}

function configEnvoyee(): ConfigPhase {
  const appel = vi.mocked(ajouterPhase).mock.calls[0]
  if (appel === undefined) throw new Error('aucun POST de phase n’a été émis')
  return appel[1]
}

describe('l’ancre d’un prélèvement', () => {
  it('poste l’identité de l’étape source, jamais son rang', async () => {
    monter([AMONT, SECONDE])
    await screen.findAllByRole('listitem')

    await userEvent.click(screen.getByRole('checkbox', { name: /Alimentée par une phase/ }))
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Phase source' }),
      screen.getByRole('option', { name: /Phase 2 —/ }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter la phase' }))

    const sources = configEnvoyee().sources ?? []
    expect(sources).toHaveLength(1)
    // 102, l'**identité** de l'étape de rang 2 — et surtout pas `2`.
    expect(sources[0]?.etape_source_id).toBe(102)
  })

  it('propose les phases antérieures sous leur rang, l’identité restant invisible', async () => {
    // Le pendant du test ci-dessus : l'organisateur continue de lire « Phase 1 », « Phase 2 ».
    // Changer l'ancre ne devait rien changer à ce qu'il voit — c'est le CA « comportement
    // observable inchangé ».
    monter([AMONT, SECONDE])
    await screen.findAllByRole('listitem')

    await userEvent.click(screen.getByRole('checkbox', { name: /Alimentée par une phase/ }))

    const options = screen
      .getAllByRole('option')
      .map((option) => option.textContent)
      // ⚠️ `\d` et non `'Phase '` : l'invite du sélecteur s'appelle « Phase source… ».
      .filter((libelle) => /^Phase \d/.test(libelle ?? ''))
    expect(options).toHaveLength(2)
    expect(options[0]).toMatch(/^Phase 1 —/)
    expect(options[1]).toMatch(/^Phase 2 —/)
  })
})
