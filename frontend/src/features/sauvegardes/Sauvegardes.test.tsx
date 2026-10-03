// Écran « Sauvegardes » (E11US006) : ce qui s'affiche en clair, et ce qui part au serveur.

import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { enregistrerJetonAdmin } from '../../shared/api/client'
import { Sauvegardes } from './Sauvegardes'
import { taille } from './presentation'

const LISTE = [
  {
    nom: 'avant-restauration-20261003-110000.db',
    nature: 'avant_restauration',
    prise_le: '2026-10-03T11:00:00Z',
    taille_octets: 2_621_440,
  },
  {
    nom: 'kervignarc-20261003-090000.db',
    nature: 'periodique',
    prise_le: '2026-10-03T09:00:00Z',
    taille_octets: 512,
  },
]

function enveloppe() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

function json(corps: unknown, status = 200) {
  return new Response(JSON.stringify(corps), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function serveur(reponses: Record<string, () => Response>) {
  const fetch = vi.fn<typeof globalThis.fetch>(async (entree) => {
    const reponse = reponses[String(entree)]
    if (reponse === undefined) throw new Error(`route non prévue : ${String(entree)}`)
    return reponse()
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

beforeEach(() => {
  vi.unstubAllGlobals()
  enregistrerJetonAdmin(() => 'jeton-admin')
})

const ligne = (nature: string) => screen.getByRole('row', { name: new RegExp(nature) })

describe('CA E11US006 — sauvegardes', () => {
  it('liste les sauvegardes dans l’ordre du serveur, nature et taille en clair', async () => {
    serveur({ '/api/v1/sauvegardes': () => json(LISTE) })
    render(<Sauvegardes />, { wrapper: enveloppe() })

    const lignes = await screen.findAllByRole('row')
    expect(lignes.slice(1).map((l) => within(l).getAllByRole('cell')[1]?.textContent)).toEqual([
      'Copie avant restauration',
      'Automatique',
    ])
    expect(ligne('Automatique')).toHaveTextContent('1 Ko')
    expect(ligne('Copie avant restauration')).toHaveTextContent('2,5 Mo')
  })

  it('dit qu’il n’y a encore aucune sauvegarde', async () => {
    serveur({ '/api/v1/sauvegardes': () => json([]) })
    render(<Sauvegardes />, { wrapper: enveloppe() })

    expect(await screen.findByText(/Aucune sauvegarde pour l’instant/)).toBeInTheDocument()
  })

  it('vérifier affiche le verdict en clair, pas sa valeur brute', async () => {
    serveur({
      '/api/v1/sauvegardes': () => json(LISTE),
      '/api/v1/sauvegardes/kervignarc-20261003-090000.db/verification': () =>
        json({ nom: 'kervignarc-20261003-090000.db', verdict: 'version_differente' }),
    })
    render(<Sauvegardes />, { wrapper: enveloppe() })
    await screen.findAllByRole('row')

    fireEvent.click(within(ligne('Automatique')).getByRole('button', { name: /Vérifier/ }))

    expect(await within(ligne('Automatique')).findByRole('status')).toHaveTextContent(
      'D’une autre version de l’application',
    )
  })

  it('restaurer demande confirmation, puis nomme la copie de l’état précédent', async () => {
    const fetch = serveur({
      '/api/v1/sauvegardes': () => json(LISTE),
      '/api/v1/sauvegardes/kervignarc-20261003-090000.db/restauration': () =>
        json({
          restauree: 'kervignarc-20261003-090000.db',
          copie_de_securite: 'avant-restauration-20261003-120000.db',
        }),
    })
    render(<Sauvegardes />, { wrapper: enveloppe() })
    await screen.findAllByRole('row')

    fireEvent.click(within(ligne('Automatique')).getByRole('button', { name: 'Restaurer…' }))
    expect(fetch).toHaveBeenCalledTimes(1) // rien ne part avant la confirmation
    fireEvent.click(screen.getByRole('button', { name: 'Restaurer' }))

    expect(await screen.findByText(/Base restaurée/)).toHaveTextContent(
      'avant-restauration-20261003-120000.db',
    )
    const appel = fetch.mock.calls.find(([chemin]) => String(chemin).endsWith('/restauration'))
    expect(appel?.[1]?.method).toBe('POST')
  })

  it('un refus du serveur s’affiche', async () => {
    serveur({
      '/api/v1/sauvegardes': () => json(LISTE),
      '/api/v1/sauvegardes/kervignarc-20261003-090000.db/restauration': () =>
        json(
          {
            code: 'sauvegarde_non_restaurable',
            message: 'La sauvegarde ne peut pas être restaurée (corrompue).',
            details: { verdict: 'corrompue' },
          },
          400,
        ),
    })
    render(<Sauvegardes />, { wrapper: enveloppe() })
    await screen.findAllByRole('row')

    fireEvent.click(within(ligne('Automatique')).getByRole('button', { name: 'Restaurer…' }))
    fireEvent.click(screen.getByRole('button', { name: 'Restaurer' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/ne peut pas être restaurée/)
    expect(screen.queryByText(/Base restaurée/)).not.toBeInTheDocument()
  })
})

describe('taille', () => {
  it('arrondit en Ko sous le mégaoctet, sans jamais afficher 0', () => {
    expect(taille(10)).toBe('1 Ko')
    expect(taille(300 * 1024)).toBe('300 Ko')
    expect(taille(1024 * 1024)).toBe('1 Mo')
  })
})
