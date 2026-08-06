// Écran d'accès administrateur — l'étiquetage des champs (E17US003, planche A01).
//
// Ce test tient **une puce de CA que l'œil ne suffit pas à vérifier** : « les champs ont un libellé
// visible au-dessus ; un `placeholder` n'est pas un libellé ». L'US a remplacé les `placeholder` +
// `aria-label` par un `<label>` enveloppant — meilleur, mais **fragile** : l'association est
// implicite, et un composant de champ partagé introduit plus tard la casserait sans rien faire
// rougir. Le champ redeviendrait alors anonyme pour un lecteur d'écran.
//
// `getByLabelText` est précisément l'assertion qui l'interdit : elle échoue si l'association se
// perd, quelle qu'en soit la cause.

import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ConnexionAdmin } from './ConnexionAdmin'

function enveloppe() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

/** L'écran interroge le serveur pour savoir s'il y a **déjà** un accès configuré ; les deux réponses
 *  donnent deux formulaires différents, et les deux doivent étiqueter leurs champs. */
function repondreConfigure(configure: boolean) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify({ configure }), { status: 200 })),
  )
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

describe('CA — les champs ont un libellé visible, pas un placeholder', () => {
  it('la connexion étiquette identifiant et mot de passe', async () => {
    repondreConfigure(true)
    render(<ConnexionAdmin />, { wrapper: enveloppe() })

    expect(await screen.findByLabelText(/identifiant/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/mot de passe/i)).toBeInTheDocument()
    // `getByLabelText` matche aussi un `aria-label` — donc le retour au `placeholder` + `aria-label`
    // que cette US a précisément retiré repasserait au vert. C'est le caractère **visible** du
    // libellé que le CA demande : on l'assert séparément.
    expect(screen.getByText('Identifiant')).toBeVisible()
    expect(screen.getByText('Mot de passe')).toBeVisible()
  })

  it('le premier accès étiquette aussi sa confirmation', async () => {
    repondreConfigure(false)
    render(<ConnexionAdmin />, { wrapper: enveloppe() })

    expect(await screen.findByLabelText(/identifiant/i)).toBeInTheDocument()
    // `getByLabelText` est exact par défaut sur le texte accessible : « Mot de passe » et
    // « Confirmer le mot de passe » sont bien deux champs distincts.
    expect(screen.getByLabelText('Confirmer le mot de passe')).toBeInTheDocument()
  })
})
