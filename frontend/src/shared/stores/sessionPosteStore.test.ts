// Tests du `sessionPosteStore` — **mode poste persistant** (E04US001, correctif de revue D-1/D-2).
//
// Garde-fou du contrat qui distingue « ce navigateur est un poste » (intention persistante) de la
// simple présence d'un jeton : une session **révoquée** (jeton perdu) doit laisser la tablette sur
// le **rattachement**, jamais la renvoyer vers l'admin (D-13) ; seul un **détachement explicite**
// quitte le mode poste. Le thème (D-26) survit aux deux. Tests en environnement node : la garde SSR
// d'`appliquerTheme` (`typeof document`) rend le store importable sans DOM.

import { beforeEach, describe, expect, it } from 'vitest'
import { useSessionPosteStore } from './sessionPosteStore'

const cible = { tournoi_id: 1, cible_index: 3 }

beforeEach(() => {
  useSessionPosteStore.setState({ jeton: null, poste: null, theme: null, estPoste: false })
})

describe('sessionPosteStore — mode poste persistant', () => {
  it('un rattachement pose le jeton, la cible et marque le navigateur comme poste', () => {
    useSessionPosteStore.getState().definir({ jeton: 'JETON', poste: cible })

    const s = useSessionPosteStore.getState()
    expect(s.jeton).toBe('JETON')
    expect(s.poste).toEqual(cible)
    expect(s.estPoste).toBe(true)
  })

  it("une révocation (effacer) perd la session mais RESTE un poste — pas de bascule vers l'admin", () => {
    useSessionPosteStore.getState().definir({ jeton: 'JETON', poste: cible })

    useSessionPosteStore.getState().effacer()

    const s = useSessionPosteStore.getState()
    expect(s.jeton).toBeNull()
    expect(s.poste).toBeNull()
    expect(s.estPoste).toBe(true) // cœur du correctif D-2 : reste un poste → formulaire de rattachement
  })

  it('un détachement explicite (detacher) quitte le mode poste', () => {
    useSessionPosteStore.getState().definir({ jeton: 'JETON', poste: cible })

    useSessionPosteStore.getState().detacher()

    const s = useSessionPosteStore.getState()
    expect(s.jeton).toBeNull()
    expect(s.poste).toBeNull()
    expect(s.estPoste).toBe(false)
  })

  it("l'arrivée par le QR (entrerModePoste) marque le navigateur comme poste avant tout rattachement", () => {
    useSessionPosteStore.getState().entrerModePoste()

    expect(useSessionPosteStore.getState().estPoste).toBe(true)
  })

  it('le thème est mémorisé et survit à une révocation', () => {
    useSessionPosteStore.getState().definirTheme('sombre')
    expect(useSessionPosteStore.getState().theme).toBe('sombre')

    useSessionPosteStore.getState().definir({ jeton: 'J', poste: cible })
    useSessionPosteStore.getState().effacer()

    expect(useSessionPosteStore.getState().theme).toBe('sombre')
  })
})
