// « Importer une liste » (E02US007) — CA « rapport » et arbitrage 4 : aperçu sans écriture, homonymes
// cochés par l'admin, puis confirmation. ⚠️ On monte l'écran Inscriptions, pas le composant seul :
// un import détaché de l'écran resterait vert autrement.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { InscriptionsAdmin } from '../admin/InscriptionsAdmin'
import type { LigneRapport, RapportImport } from './api'
import { apercuImport, confirmerImport } from './api'

vi.mock('./api', () => ({ apercuImport: vi.fn(), confirmerImport: vi.fn() }))
vi.mock('../archers/Archers', () => ({ Archers: () => null }))
vi.mock('../archers/NouvelArcher', () => ({ NouvelArcher: () => null }))
vi.mock('../archers/hooks', () => ({ useArchers: () => ({ data: [] }) }))
vi.mock('../paiements/hooks', () => ({ useArchersNonRegles: () => null }))
vi.mock('../placement/hooks', () => ({ usePlansDuTournoi: () => [] }))
vi.mock('../categories/hooks', () => ({
  useCategories: () => ({ data: [{ id: 5, libelle: 'Femmes' }] }),
}))

function ligne(numero: number, surcharge: Partial<LigneRapport>): LigneRapport {
  return {
    numero,
    decision: 'creer',
    motif: null,
    nom: 'DUPONT',
    prenom: 'JEANNE',
    licence: '1234567A',
    depart_numero: 1,
    categorie_id: 5,
    club: 'KERVIGNAC',
    club_a_creer: false,
    homonyme_de: null,
    fiche: null,
    ...surcharge,
  }
}

const APERCU: RapportImport = {
  source: 'ianseo',
  importables: 1,
  rejetees: 1,
  homonymes: 1,
  colonnes_ignorees: [],
  lignes: [
    ligne(1, {}),
    ligne(2, { decision: 'rejetee', motif: "Le départ n° 9 n'existe pas", categorie_id: null }),
    ligne(3, { decision: 'homonyme', licence: null, homonyme_de: 'Jeanne Martin' }),
    ligne(4, { decision: 'inscrire', nom: null, prenom: null, fiche: 'Paul Durand' }),
  ],
}

const FICHIER = new File(['...'], 'inscrits.csv', { type: 'text/csv' })

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <InscriptionsAdmin tournoiId={7} ouvrir={null} onOuvrir={vi.fn()} />
    </QueryClientProvider>,
  )
}

async function deposer() {
  await userEvent.click(screen.getByRole('button', { name: 'Importer une liste' }))
  await userEvent.upload(screen.getByLabelText("Fichier d'inscrits"), FICHIER)
}

describe('Importer une liste', () => {
  beforeEach(() => {
    vi.mocked(apercuImport).mockReset().mockResolvedValue(APERCU)
    vi.mocked(confirmerImport)
      .mockReset()
      .mockResolvedValue({ ...APERCU, importables: 2, homonymes: 0 })
  })

  it('déposer le fichier rend le rapport sans rien écrire', async () => {
    monter()
    await deposer()

    expect(await screen.findByText(/Rejetée : Le départ n° 9 n'existe pas/)).toBeTruthy()
    expect(screen.getByText('Nouvelle fiche')).toBeTruthy()
    // Résult'Arc ne porte pas de nom : la ligne montre la fiche que la licence désigne.
    expect(screen.getByText('Paul Durand')).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain('1 à importer, 1 rejetée, 1 homonyme')
    expect(apercuImport).toHaveBeenCalledWith(7, FICHIER)
    expect(confirmerImport).not.toHaveBeenCalled()
  })

  it("un homonyme n'est confirmé que coché, et le bouton compte les lignes écrites", async () => {
    monter()
    await deposer()
    expect(await screen.findByRole('button', { name: 'Importer 1 ligne' })).toBeTruthy()

    await userEvent.click(screen.getByRole('checkbox', { name: /Homonyme de Jeanne Martin/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Importer 2 lignes' }))

    expect(confirmerImport).toHaveBeenCalledWith(7, FICHIER, [3])
    expect((await screen.findByRole('status')).textContent).toContain('Import terminé')
  })

  it("rien d'importable : le bouton reste inactif", async () => {
    vi.mocked(apercuImport).mockResolvedValue({
      ...APERCU,
      importables: 0,
      homonymes: 0,
      lignes: APERCU.lignes.slice(1, 2),
    })
    monter()
    await deposer()

    const bouton = await screen.findByRole('button', { name: 'Importer 0 ligne' })
    expect((bouton as HTMLButtonElement).disabled).toBe(true)
  })
})
