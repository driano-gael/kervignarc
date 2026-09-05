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
// Hissé hors du sélecteur : construit à l'intérieur, il changeait d'identité à chaque rendu et
// son compteur d'appels devenait inexploitable pour un test futur (relevé en revue).
const entrerModePoste = vi.fn()

vi.mock('../shared/stores/sessionPosteStore', () => ({
  useSessionPosteStore: (selecteur: (etat: unknown) => unknown) =>
    selecteur({ estPoste, poste: null, entrerModePoste }),
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
// contenu. `EspaceScoreur` annonce le code reçu — c'est ainsi qu'on prouve qu'il lui parvient, puis
// qu'il lui est retiré.
vi.mock('../features/poste/EspacePoste', () => ({
  EspacePoste: () => <p>écran de poste</p>,
}))
vi.mock('../features/admin/CoquilleAdmin', () => ({ CoquilleAdmin: () => <p>admin</p> }))
vi.mock('../features/public/AccueilPublic', () => ({ AccueilPublic: () => <p>public</p> }))
// La doublure **enregistre** ce qu'elle reçoit à chaque rendu : c'est la seule façon d'observer
// que le shell ne GARDE pas le code (cf. le test « consomme »).
const codesRecus: (string | null)[] = []
vi.mock('../features/scoreur-session/EspaceScoreur', () => ({
  EspaceScoreur: ({ codeUrl }: { codeUrl: string | null }) => {
    codesRecus.push(codeUrl)
    return <p>scoreur : {String(codeUrl)}</p>
  },
}))
vi.mock('../shared/realtime/IndicateurConnexion', () => ({ IndicateurConnexion: () => null }))

function placerUrl(url: string) {
  window.history.replaceState(null, '', url)
}

describe('App — arrivée par le QR d’un scoreur', () => {
  beforeEach(() => {
    estPoste = false
    entrerModePoste.mockClear()
    codesRecus.length = 0
    placerUrl('/')
  })

  it('sert l’espace scoreur avec le code, et retire le code de l’adresse', async () => {
    placerUrl('/scoreur#code=AB12CD')

    render(<App />)

    // L'espace reçoit le code, puis l'écran retombe à `null` — l'effacement de l'adresse notifie
    // ses abonnés (`useCodeScoreurDArrivee`), donc la transition est visible dans le DOM.
    expect(await screen.findByText('scoreur : null')).toBeInTheDocument()
    expect(codesRecus[0]).toBe('AB12CD')
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

  it('CONSOMME le code : il est transmis une fois, puis plus jamais', async () => {
    // ⚠️ **Bloquant de la 2ᵉ passe de revue.** Le shell gardait le code pour toute la durée de
    // l'onglet, et `FormulaireCode` rejoue la connexion à chaque montage : « Fermer ma session »
    // rouvrait donc la session, et « Changer de rôle » rendait l'appareil en y laissant celle du
    // scoreur précédent. L'oracle est la SUITE des valeurs reçues, pas la première.
    placerUrl('/scoreur#code=AB12CD')

    render(<App />)
    await screen.findByText('scoreur : null')

    // ⚠️ **Aucun `rerender` ici, et c'est le point.** Les deux rédactions précédentes en avaient un :
    // elles prouvaient « le shell ne mémorise pas » sans jamais montrer que le code est retiré **de
    // lui-même**. Le trou ne se refermait alors que parce qu'un store voisin re-rendait au bon
    // moment — invariant qu'aucun texte n'écrivait et qu'un reset partiel du store aurait cassé.
    // ⚠️ La **suite entière**, pas ses deux extrémités : `['AB12CD', 'AB12CD', null]` passait, alors
    // que le titre promet « une fois ». Chaque rendu supplémentaire portant le code est une fenêtre
    // de plus où il vit dans un élément committé. ⚠️ Casserait sous `StrictMode` (rendu doublé) —
    // c'est voulu : il faudrait alors décider ce que « une fois » signifie, pas relâcher l'oracle.
    expect(codesRecus).toEqual(['AB12CD', null])
  })

  it('reçoit un code arrivé APRÈS le chargement (scan sur un onglet déjà ouvert)', async () => {
    // ⚠️ Le chemin que le mécanisme d'abonnement avait laissé ouvert : une URL qui ne diffère que
    // par le fragment est une navigation *same-document*, sans rechargement. Sans l'écoute de
    // `hashchange`, le code n'arrivait jamais **et restait dans la barre d'adresse** — sur l'écran
    // même où le scoreur vient de demander son QR (revue ciblée du 05/09/2026).
    placerUrl('/scoreur')
    render(<App />)
    await screen.findByText('scoreur : null')

    window.location.hash = '#code=AB12CD'

    expect(await screen.findByText('scoreur : null')).toBeInTheDocument()
    expect(codesRecus).toContain('AB12CD')
    expect(window.location.hash).toBe('')
  })
})
