// Rendu de l'écran « Journal d'audit » (E16US016).
//
// ⚠️ Ce fichier existe pour la raison que `DETTE-085` documente : `tsc` ne voit pas un écran qui
// calcule tout et ne rend rien, et aucun test de service ne monte un composant. L'US livre un
// écran **entièrement neuf** sur une route que personne n'appelait — sans test de rendu, « le
// journal se consulte » ne serait prouvé nulle part.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { Audit } from './Audit'
import type { EntreeAudit } from './api'

let journal: EntreeAudit[] = []

vi.mock('./api', () => ({
  getAudit: () => Promise.resolve(journal),
}))

function entree(partiel: Partial<EntreeAudit> & { id: number }): EntreeAudit {
  return {
    tournoi_id: 1,
    action: 'validation',
    auteur: 'DURAND Jean',
    horodatage: '2026-09-18T08:12:04Z',
    objet: 'Série 1 — cible 4A',
    avant: null,
    apres: null,
    ...partiel,
  }
}

function monter() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 30_000 } },
  })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(<Audit tournoiId={1} />, { wrapper: Enveloppe })
}

describe('Audit — le journal se consulte', () => {
  beforeEach(() => {
    journal = []
  })

  it('liste les actes, avec qui et sur quoi', async () => {
    journal = [
      entree({ id: 1, auteur: 'LE GUEN Anne', objet: 'Série 1' }),
      entree({ id: 2, action: 'forfait', auteur: 'MOREAU Yves', objet: 'Cible 14' }),
    ]

    monter()

    expect(await screen.findByText('LE GUEN Anne')).toBeInTheDocument()
    expect(screen.getByText('MOREAU Yves')).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Forfait' })).toBeInTheDocument()
    expect(screen.getByText('Cible 14')).toBeInTheDocument()
  })

  it('compte les entrées et, à part, les corrections', async () => {
    journal = [
      entree({ id: 1 }),
      entree({ id: 2, action: 'correction_score', avant: '8', apres: '9' }),
      entree({ id: 3, action: 'annulation_validation' }),
    ]

    monter()

    expect(await screen.findByText('3 entrées')).toBeInTheDocument()
    expect(screen.getByText('2 corrections')).toBeInTheDocument()
  })

  it('déplie l’avant/après d’une correction, et ne promet rien sur une validation', async () => {
    journal = [
      entree({
        id: 1,
        action: 'correction_score',
        objet: 'Volée 7, flèche 2',
        avant: '8',
        apres: '9',
      }),
    ]

    monter()
    await screen.findByText('Volée 7, flèche 2')
    await userEvent.click(screen.getByText('Avant / après'))

    expect(screen.getByText('8')).toBeInTheDocument()
    expect(screen.getByText('9')).toBeInTheDocument()
  })

  it('filtre sur le type d’acte', async () => {
    journal = [
      entree({ id: 1, auteur: 'LE GUEN Anne' }),
      entree({ id: 2, action: 'forfait', auteur: 'MOREAU Yves' }),
    ]

    monter()
    await screen.findByText('LE GUEN Anne')
    await userEvent.selectOptions(screen.getByLabelText(/Type d’acte/), 'forfait')

    expect(screen.getByText('MOREAU Yves')).toBeInTheDocument()
    expect(screen.queryByText('LE GUEN Anne')).not.toBeInTheDocument()
  })

  it('cherche un archer sans que la casse ni les accents comptent', async () => {
    journal = [
      entree({ id: 1, objet: 'Cible 4 — LE GUÉN Anne' }),
      entree({ id: 2, objet: 'Cible 9 — MOREAU Yves' }),
    ]

    monter()
    await screen.findByText(/LE GUÉN Anne/)
    await userEvent.type(screen.getByLabelText(/Rechercher/), 'le guen')

    expect(screen.getByText(/LE GUÉN Anne/)).toBeInTheDocument()
    expect(screen.queryByText(/MOREAU Yves/)).not.toBeInTheDocument()
  })

  it('dit qu’aucun acte n’est tracé sans faire croire à une panne', async () => {
    journal = []

    monter()

    expect(await screen.findByText(/Aucun acte tracé/)).toBeInTheDocument()
  })

  it('distingue « rien à voir » de « rien ne correspond »', async () => {
    journal = [entree({ id: 1, auteur: 'DURAND Jean' })]

    monter()
    await screen.findByText('DURAND Jean')
    await userEvent.type(screen.getByLabelText(/Rechercher/), 'zzz')

    expect(screen.getByText(/Aucune entrée ne correspond/)).toBeInTheDocument()
    expect(screen.queryByText(/Aucun acte tracé/)).not.toBeInTheDocument()
  })

  it('pagine au-delà d’une page et borne la page courante quand le filtre réduit la liste', async () => {
    // ⚠️ Le second volet est le vrai piège : filtrer depuis la page 2 laissait, en première
    // rédaction, un tableau vide sous une pagination qui annonçait encore des pages.
    journal = Array.from({ length: 60 }, (_, index) =>
      entree({ id: index + 1, auteur: `ARCHER ${index + 1}` }),
    )

    monter()
    await screen.findByText('ARCHER 1')
    expect(screen.getByText('Page 1 sur 2')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Suivant' }))
    expect(screen.getByText('ARCHER 60')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText(/Rechercher/), 'ARCHER 3')
    expect(screen.getByText('ARCHER 3')).toBeInTheDocument()
    expect(screen.queryByText(/Page \d+ sur/)).not.toBeInTheDocument()
  })
})
