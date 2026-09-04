// Arrivée du scoreur **par le QR** (E16US015) : la session s'ouvre sans retaper le code.
//
// Fichier distinct d'`EspaceScoreur.test.tsx`, qui double le store sur une session **déjà ouverte**
// pour garder `DETTE-056` : ici il faut l'inverse (aucune session), et mélanger les deux doublures
// affaiblirait celle qui garde la dette. ⚠️ L'**effacement** de l'adresse ne se teste pas ici mais
// dans `src/app/App.entree.test.tsx` : depuis la revue du 04/09/2026 il vit au shell, parce qu'une
// tablette rattachée ne monte jamais ce composant.

import { render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EspaceScoreur } from './EspaceScoreur'

const MUTATION = { mutate: vi.fn(), isPending: false, isError: false, error: null }

vi.mock('../../shared/stores/sessionScoreurStore', () => ({
  useSessionScoreurStore: (selecteur: (etat: unknown) => unknown) =>
    selecteur({ scoreur: null, jeton: null }),
}))

vi.mock('./hooks', () => ({
  useConnexionScoreur: () => MUTATION,
  useDeconnexionScoreur: () => MUTATION,
}))

describe('arrivée par le QR d’un scoreur', () => {
  beforeEach(() => MUTATION.mutate.mockClear())

  it('ouvre la session avec le code reçu du shell, sans geste', () => {
    render(<EspaceScoreur codeUrl="AB12CD" />)

    expect(MUTATION.mutate).toHaveBeenCalledWith('AB12CD')
    expect(screen.getByLabelText('Code du scoreur')).toHaveValue('AB12CD')
  })

  it('ne tente la connexion qu’une fois, même au double montage StrictMode', () => {
    render(
      <StrictMode>
        <EspaceScoreur codeUrl="AB12CD" />
      </StrictMode>,
    )

    expect(MUTATION.mutate).toHaveBeenCalledTimes(1)
  })

  it('ne tente rien sans code (entrée normale, saisie à la main)', () => {
    render(<EspaceScoreur />)

    expect(MUTATION.mutate).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Code du scoreur')).toHaveValue('')
  })

  it('ne tente rien sur un code vide — une connexion à blanc n’est pas une arrivée', () => {
    render(<EspaceScoreur codeUrl="" />)

    expect(MUTATION.mutate).not.toHaveBeenCalled()
  })
})
