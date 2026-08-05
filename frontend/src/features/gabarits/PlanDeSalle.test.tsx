// Aperçu des **couloirs de tir** sur le plan de salle (E16US001).
//
// C'est la seule capacité nouvelle de l'US : le CA veut que l'écran « rende visible » ce qu'il
// règle, au lieu de le laisser deviner. Deux choses s'y jouent, et aucune n'est évidente à la
// lecture du code :
//
// 1. l'aperçu suit la **saisie**, pas l'état enregistré — réduire une cible doit éteindre les
//    lettres tout de suite, sinon l'écran affiche un plan qui n'est plus celui qu'on compose ;
// 2. l'aperçu ne doit **rien enregistrer** au passage : c'est un rendu, pas une mutation.
//
// On double les appels HTTP seulement ; les hooks et le `QueryClient` sont ceux de production
// (même parti que `phases/Profondeur.test.tsx`), sans quoi le test ne dirait rien du vrai écran.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ajusterGabarit, type Gabarit } from './api'
import { FormulaireAjustement } from './PlanDeSalle'

vi.mock('./api', () => ({
  ajusterGabarit: vi.fn(),
  getGabarits: vi.fn(),
  getGabaritDuTournoi: vi.fn(),
  appliquerGabarit: vi.fn(),
  creerGabarit: vi.fn(),
  modifierGabarit: vi.fn(),
  supprimerGabarit: vi.fn(),
}))

function gabarit(capacites: number[]): Gabarit {
  return {
    id: 7,
    nom: 'Salle municipale',
    nb_cibles: capacites.length,
    tournoi_id: 1,
    cibles: capacites.map((capacite, index) => ({
      index: index + 1,
      capacite,
      positions: Array.from({ length: capacite }, (_, rang) => String.fromCharCode(65 + rang)),
    })),
  }
}

function poser(capacites: number[]) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<FormulaireAjustement tournoiId={1} gabarit={gabarit(capacites)} />, {
    wrapper: Enveloppe,
  })
}

// Les lettres éteintes portent le modificateur ; les occupables ne l'ont pas.
function couloir(lettre: string): HTMLElement {
  // L'aperçu est `aria-hidden` (l'état n'est porté que par le style), donc hors de l'arbre
  // accessible : on le lit par le texte, pas par un rôle.
  const case_ = screen.getAllByText(lettre).find((n) => n.className.includes('plan-cible__couloir'))
  if (!case_) throw new Error(`Aucune case de couloir « ${lettre} »`)
  return case_
}

const eteint = (lettre: string) => couloir(lettre).className.includes('--inactif')

// Les compteurs d'appel sont partagés dans le fichier (pas de `clearMocks` global côté vite).
beforeEach(() => vi.clearAllMocks())

describe('aperçu des couloirs de tir', () => {
  it('montre les couloirs occupables pleins et les autres éteints', () => {
    poser([4])

    expect(eteint('A')).toBe(false)
    expect(eteint('B')).toBe(false)
    expect(eteint('C')).toBe(false)
    expect(eteint('D')).toBe(false)
  })

  it('éteint C et D dès qu’on réduit la cible, sans attendre l’enregistrement', async () => {
    poser([4])

    await userEvent.selectOptions(screen.getByLabelText('Couloirs de tir de la cible 1'), '2')

    expect(eteint('A')).toBe(false)
    expect(eteint('B')).toBe(false)
    expect(eteint('C')).toBe(true)
    expect(eteint('D')).toBe(true)
    // Garde-fou contre un enregistrement implicite : rien ne doit partir sans « Enregistrer ».
    expect(vi.mocked(ajusterGabarit)).not.toHaveBeenCalled()
  })

  it('annonce un plafond, pas un effectif', () => {
    // Le mot « Jusqu'à » est la correction de fond de la revue : un plafond n'est pas une égalité.
    poser([4])

    expect(screen.getByRole('option', { name: "Jusqu'à 2 couloirs de tir" })).toBeTruthy()
    expect(screen.getByRole('option', { name: "Jusqu'à 1 couloir de tir" })).toBeTruthy()
  })

  it('rallume les couloirs quand on remonte le plafond', async () => {
    poser([2])

    expect(eteint('D')).toBe(true)

    await userEvent.selectOptions(screen.getByLabelText('Couloirs de tir de la cible 1'), '4')

    expect(eteint('D')).toBe(false)
  })

  it('revient au plan enregistré quand on réinitialise', async () => {
    poser([4])

    await userEvent.selectOptions(screen.getByLabelText('Couloirs de tir de la cible 1'), '1')
    expect(eteint('B')).toBe(true)

    await userEvent.click(screen.getByRole('button', { name: 'Réinitialiser' }))

    expect(eteint('B')).toBe(false)
  })
})
