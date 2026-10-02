// Écran « Compte administrateur » (E10US006) : ce qui part au serveur, et ce qui reste à l'écran
// quand il refuse — un refus ne doit pas déconnecter l'admin (le client purge sur 401 seulement).

import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { enregistrerJetonAdmin, enregistrerSurNonAutorise } from '../../shared/api/client'
import { CompteAdmin } from './CompteAdmin'

function enveloppe() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

function saisir(libelle: string, valeur: string) {
  fireEvent.change(screen.getByLabelText(libelle), { target: { value: valeur } })
}

beforeEach(() => {
  vi.unstubAllGlobals()
  enregistrerJetonAdmin(() => 'jeton-admin')
})

describe('CA E10US006 — modifier les identifiants', () => {
  it('envoie le mot de passe actuel et seulement les champs remplis, puis confirme', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>(async () => new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetch)
    render(<CompteAdmin />, { wrapper: enveloppe() })

    saisir('Mot de passe actuel', 'ancien')
    saisir('Nouveau mot de passe (vide = inchangé)', 'neuf')
    saisir('Confirmer le nouveau mot de passe', 'neuf')
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(await screen.findByRole('status')).toHaveTextContent(/autres appareils/)
    // Une nouvelle saisie efface le succès précédent : il ne parle plus de ce qui est tapé.
    saisir('Mot de passe actuel', 'n')
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    const [chemin, options = {}] = fetch.mock.lastCall ?? []
    expect(chemin).toBe('/api/v1/auth/identifiants')
    expect(options.method).toBe('PATCH')
    expect(JSON.parse(String(options.body))).toEqual({
      mot_de_passe_actuel: 'ancien',
      nouveau_mot_de_passe: 'neuf',
    })
    expect(new Headers(options.headers).get('Authorization')).toBe('Bearer jeton-admin')
  })

  it('un mot de passe actuel faux s’affiche sans purger la session', async () => {
    const purge = vi.fn()
    enregistrerSurNonAutorise(purge)
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              code: 'mot_de_passe_actuel_incorrect',
              message: 'Le mot de passe actuel est incorrect.',
            }),
            { status: 403 },
          ),
      ),
    )
    render(<CompteAdmin />, { wrapper: enveloppe() })

    saisir('Mot de passe actuel', 'faux')
    saisir('Nouvel identifiant (vide = inchangé)', 'arbitre')
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/mot de passe actuel/i)
    expect(purge).not.toHaveBeenCalled()
  })

  it('n’envoie rien sans mot de passe actuel, sans changement, ou si la confirmation diffère', () => {
    render(<CompteAdmin />, { wrapper: enveloppe() })
    const bouton = screen.getByRole('button', { name: 'Enregistrer' })

    saisir('Nouvel identifiant (vide = inchangé)', 'arbitre')
    expect(bouton).toBeDisabled()

    saisir('Mot de passe actuel', 'ancien')
    expect(bouton).toBeEnabled()

    // Confirmation encore vide : bouton bloqué, mais pas d'alerte avant que l'admin y arrive.
    saisir('Nouveau mot de passe (vide = inchangé)', 'neuf')
    expect(bouton).toBeDisabled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    saisir('Confirmer le nouveau mot de passe', 'autre')
    expect(bouton).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent(/ne correspondent pas/)

    saisir('Confirmer le nouveau mot de passe', '')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(bouton).toBeDisabled()

    saisir('Nouvel identifiant (vide = inchangé)', '')
    saisir('Nouveau mot de passe (vide = inchangé)', '')
    expect(bouton).toBeDisabled()
  })

  it('une frappe pendant l’envoi n’escamote pas le succès de la rotation', async () => {
    let repondre: (reponse: Response) => void = () => {}
    const fetch = vi.fn<typeof globalThis.fetch>(
      () => new Promise((resoudre) => (repondre = resoudre)),
    )
    vi.stubGlobal('fetch', fetch)
    render(<CompteAdmin />, { wrapper: enveloppe() })

    saisir('Mot de passe actuel', 'ancien')
    saisir('Nouvel identifiant (vide = inchangé)', 'arbitre')
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    saisir('Nouvel identifiant (vide = inchangé)', 'arbitre2')
    repondre(new Response(null, { status: 204 }))

    expect(await screen.findByRole('status')).toHaveTextContent(/Identifiants modifiés/)
  })
})
