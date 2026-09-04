// Arrivée du scoreur **par le QR** (E16US015) : la session s'ouvre sans retaper le code.
//
// Fichier distinct d'`EspaceScoreur.test.tsx`, qui double le store sur une session **déjà ouverte**
// pour garder `DETTE-056` : ici il faut l'inverse (aucune session), et mélanger les deux doublures
// dans un même module reviendrait à affaiblir celle qui garde la dette.

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

function placerUrl(url: string) {
  window.history.replaceState(null, '', url)
}

describe('arrivée par le QR d’un scoreur', () => {
  beforeEach(() => {
    MUTATION.mutate.mockClear()
    placerUrl('/scoreur')
  })

  it('ouvre la session avec le code porté par l’URL, sans geste', () => {
    placerUrl('/scoreur?code=AB12CD')

    render(<EspaceScoreur />)

    expect(MUTATION.mutate).toHaveBeenCalledWith('AB12CD')
    expect(screen.getByLabelText('Code du scoreur')).toHaveValue('AB12CD')
  })

  it('retire le code de la barre d’adresse, sans quitter le monde scoreur', () => {
    placerUrl('/scoreur?code=AB12CD')

    render(<EspaceScoreur />)

    // Le code ne doit survivre ni dans l'historique ni dans un rechargement : un QR photographié
    // reste un risque, une URL laissée à l'écran en est un second, gratuit.
    expect(window.location.search).toBe('')
    expect(window.location.pathname).toBe('/scoreur')
  })

  it('ne tente la connexion qu’une fois, même au double montage StrictMode', () => {
    placerUrl('/scoreur?code=AB12CD')

    render(
      <StrictMode>
        <EspaceScoreur />
      </StrictMode>,
    )

    expect(MUTATION.mutate).toHaveBeenCalledTimes(1)
  })

  it('ne tente rien sans code dans l’URL (entrée normale, saisie à la main)', () => {
    render(<EspaceScoreur />)

    expect(MUTATION.mutate).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Code du scoreur')).toHaveValue('')
  })

  it('ne tente rien sur un paramètre vide — une connexion à blanc n’est pas une arrivée', () => {
    placerUrl('/scoreur?code=')

    render(<EspaceScoreur />)

    expect(MUTATION.mutate).not.toHaveBeenCalled()
  })
})
