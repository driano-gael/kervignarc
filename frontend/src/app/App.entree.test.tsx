// Le **shell** face à une arrivée par QR (E16US015, ADR-0105).
//
// ⚠️ Ce fichier existe parce que la revue du 04/09/2026 a constaté que rien ne rendait `App` : les
// tests d'entrée portaient soit sur `resoudreRole` (pur), soit sur `EspaceScoreur` monté seul. La
// précédence du verrou de poste (`D-13`) n'était donc jamais traversée — et c'est exactement là que
// le code personnel d'un scoreur restait dans la barre d'adresse d'une tablette partagée.

import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'

let estPoste = false

vi.mock('../shared/stores/sessionPosteStore', () => ({
  useSessionPosteStore: (selecteur: (etat: unknown) => unknown) =>
    selecteur({ estPoste, poste: null, entrerModePoste: vi.fn() }),
}))
vi.mock('../shared/stores/sessionRoleStore', () => ({
  useSessionRoleStore: (selecteur: (etat: unknown) => unknown) =>
    selecteur({ role: null, choisir: vi.fn() }),
}))
vi.mock('../shared/stores/sessionAdminStore', () => ({
  useSessionAdminStore: (selecteur: (etat: unknown) => unknown) => selecteur({ jeton: null }),
}))
vi.mock('../shared/stores/sessionScoreurStore', () => ({
  useSessionScoreurStore: (selecteur: (etat: unknown) => unknown) =>
    selecteur({ jeton: null, scoreur: null }),
}))

// Les quatre mondes sont doublés : ce test répond de **l'aiguillage et de l'adresse**, pas de leur
// contenu. `EspaceScoreur` annonce le code reçu — c'est ainsi qu'on prouve qu'il lui parvient
// malgré l'effacement de l'adresse, qui a lieu dans le même commit de rendu.
vi.mock('../features/poste/EspacePoste', () => ({
  EspacePoste: () => <p>écran de poste</p>,
}))
vi.mock('../features/admin/CoquilleAdmin', () => ({ CoquilleAdmin: () => <p>admin</p> }))
vi.mock('../features/public/AccueilPublic', () => ({ AccueilPublic: () => <p>public</p> }))
vi.mock('../features/scoreur-session/EspaceScoreur', () => ({
  EspaceScoreur: ({ codeUrl }: { codeUrl: string | null }) => <p>scoreur : {String(codeUrl)}</p>,
}))
vi.mock('../shared/realtime/IndicateurConnexion', () => ({ IndicateurConnexion: () => null }))

function placerUrl(url: string) {
  window.history.replaceState(null, '', url)
}

describe('App — arrivée par le QR d’un scoreur', () => {
  beforeEach(() => {
    estPoste = false
    placerUrl('/')
  })

  it('sert l’espace scoreur avec le code, et retire le code de l’adresse', async () => {
    placerUrl('/scoreur#code=AB12CD')

    render(<App />)

    expect(await screen.findByText('scoreur : AB12CD')).toBeInTheDocument()
    expect(window.location.hash).toBe('')
  })

  it('retire le code même quand le verrou de poste renvoie sur l’écran de cible', async () => {
    // ⚠️ **Le cas qui a échappé à l'auteur.** Une tablette déjà rattachée qui scanne un QR de
    // scoreur reste sur son écran (`D-13`) — mais `naviguer` **conserve** query et fragment, donc
    // sans effacement au shell le code personnel restait affiché toute la journée sur un appareil
    // partagé, et dans son historique.
    estPoste = true
    placerUrl('/scoreur#code=AB12CD')

    render(<App />)

    expect(await screen.findByText('écran de poste')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/cible')
    expect(window.location.hash).toBe('')
  })

  it('ne touche pas au `?poste=` du QR de cible en effaçant le code', async () => {
    // Non-régression : l'effacement s'exécute sur des adresses qui ne sont pas celles du scoreur.
    estPoste = true
    placerUrl('/cible?poste=ZZZ999#code=AB12CD')

    render(<App />)

    expect(await screen.findByText('écran de poste')).toBeInTheDocument()
    expect(window.location.search).toBe('?poste=ZZZ999')
    expect(window.location.hash).toBe('')
  })
})
