// Test de rendu de l'écran « Exports & impressions » (E16US007).
//
// CA : « chaque export propose ses formats disponibles ; l'ajout d'un format ne demande pas de
// toucher l'écran ». On vérifie la **propriété**, pas une capture (cf. ADR-0101 §1).
//
// ⚠️ **Monter l'écran, pas la section** : un test qui monterait `SectionExport` seule resterait
// vert après l'avoir détachée de la liste — le défaut exact de `DETTE-085`.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EntreeCatalogueExport } from './api'
import { chargerCatalogueExports, telechargerExport } from './api'
import { Exports } from './Exports'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  chargerCatalogueExports: vi.fn(),
  telechargerExport: vi.fn(),
}))

vi.mock('../departs/hooks', () => ({
  useDeparts: () => ({ data: [{ id: 3, numero: 1 }] }),
}))

const PDF = { code: 'pdf', libelle: 'PDF' }
const CSV = { code: 'csv', libelle: 'Tableur (CSV)' }

// ⚠️ Le catalogue ne porte QUE la capacité : les libellés affichés viennent de l'écran (ADR-0101).
function entree(
  identifiant: string,
  formats: { code: string; libelle: string }[],
): EntreeCatalogueExport {
  return { identifiant, formats }
}

const CATALOGUE = [
  entree('placement', [PDF, CSV]),
  entree('club-paiement', [PDF, CSV]),
  entree('feuille-de-marque', [PDF]),
]

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <Exports tournoiId={7} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(chargerCatalogueExports).mockReset()
  vi.mocked(chargerCatalogueExports).mockResolvedValue(CATALOGUE)
  vi.mocked(telechargerExport).mockReset()
  vi.mocked(telechargerExport).mockResolvedValue(undefined)
})

describe("l'écran rend ce que le catalogue annonce", () => {
  it('affiche un bouton par format de chaque document', async () => {
    monter()

    const placement = await screen.findByRole('heading', { name: 'Liste de placement' })
    const section = placement.closest('section')
    expect(section).not.toBeNull()
    expect(
      Array.from(section!.querySelectorAll('button')).map((bouton) => bouton.textContent),
    ).toEqual(['Télécharger — PDF', 'Télécharger — Tableur (CSV)'])
  })

  it("n'offre qu'un bouton à un document mono-format", async () => {
    monter()

    const feuille = await screen.findByRole('heading', { name: 'Feuille de marque' })
    const section = feuille.closest('section')
    expect(Array.from(section!.querySelectorAll('button'))).toHaveLength(1)
  })

  it("rend un format que ce fichier ne mentionne nulle part — c'est le CA", async () => {
    // Le serveur câble un format de plus ; **aucune ligne d'écran ne change**.
    vi.mocked(chargerCatalogueExports).mockResolvedValue([
      entree('club-paiement', [PDF, CSV, { code: 'ods', libelle: 'ODS' }]),
    ])
    monter()

    expect(await screen.findByRole('button', { name: 'Télécharger — ODS' })).toBeTruthy()
  })

  it('demande le document au format du bouton cliqué', async () => {
    monter()

    // ⚠️ Portée à la section : « Télécharger — Tableur (CSV) » existe aussi sous club & paiement.
    const placement = await screen.findByRole('heading', { name: 'Liste de placement' })
    const section = placement.closest('section')!
    await userEvent.click(section.querySelectorAll('button')[1]!)

    expect(telechargerExport).toHaveBeenCalledWith(
      '/api/v1/tournois/7/listes/placement?tri=cible',
      'placement-tournoi-7',
      'csv',
    )
  })
})

describe('commandes propres à un document', () => {
  it("laisse la feuille de marque inactive tant qu'aucun départ n'est choisi", async () => {
    monter()

    const feuille = await screen.findByRole('heading', { name: 'Feuille de marque' })
    const section = feuille.closest('section')!
    expect(section.querySelector('button')).toBeDisabled()
    expect(section.textContent).toContain('Choisissez le départ')
  })

  it('arme la feuille de marque une fois le départ choisi', async () => {
    monter()

    const feuille = await screen.findByRole('heading', { name: 'Feuille de marque' })
    const section = feuille.closest('section')!
    await userEvent.selectOptions(section.querySelector('select')!, '3')
    await userEvent.click(section.querySelector('button')!)

    expect(telechargerExport).toHaveBeenCalledWith(
      '/api/v1/tournois/7/departs/3/feuille-de-marque',
      'feuille-de-marque-tournoi-7-depart-3',
      'pdf',
    )
  })

  it('reporte le tri choisi dans la demande de placement', async () => {
    monter()

    const placement = await screen.findByRole('heading', { name: 'Liste de placement' })
    const section = placement.closest('section')!
    await userEvent.selectOptions(section.querySelectorAll('select')[0]!, 'nom')
    await userEvent.click(section.querySelector('button')!)

    expect(telechargerExport).toHaveBeenCalledWith(
      '/api/v1/tournois/7/listes/placement?tri=nom',
      'placement-tournoi-7',
      'pdf',
    )
  })
})

// ⚠️ Ces trois tests gardent des **correctifs de revue**. Sans eux, un futur diff qui « simplifie »
// les `&&` du rendu ferait redisparaître les états, et l'écran redeviendrait indistinguable d'un
// écran cassé — le défaut que trois axes avaient relevé (2ᵉ passe, axes B et D).
describe("l'écran dit dans quel état il est", () => {
  it('annonce le chargement plutôt que de ne rien rendre', async () => {
    vi.mocked(chargerCatalogueExports).mockReturnValue(new Promise(() => {}))
    monter()

    expect(await screen.findByText(/Chargement des documents/)).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Liste de placement' })).toBeNull()
  })

  it('annonce l’échec et propose de réessayer', async () => {
    vi.mocked(chargerCatalogueExports).mockRejectedValue(new Error('boum'))
    monter()

    expect(await screen.findByText(/Impossible de lister les documents/)).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(chargerCatalogueExports).toHaveBeenCalledTimes(2)
  })

  it('dit en clair qu’aucun document servi ne lui est connu (DETTE-095)', async () => {
    vi.mocked(chargerCatalogueExports).mockResolvedValue([entree('inconnu-au-bataillon', [PDF])])
    monter()

    expect(await screen.findByText(/aucun document connu de cet écran/)).toBeVisible()
  })

  it('ne dit « Génération… » que sur le bouton cliqué', async () => {
    vi.mocked(telechargerExport).mockReturnValue(new Promise(() => {}))
    monter()

    const placement = await screen.findByRole('heading', { name: 'Liste de placement' })
    const section = placement.closest('section')!
    await userEvent.click(section.querySelectorAll('button')[0]!)

    const libelles = Array.from(section.querySelectorAll('button')).map((b) => b.textContent)
    expect(libelles).toEqual(['Génération…', 'Télécharger — Tableur (CSV)'])
  })
})
