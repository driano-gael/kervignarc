// Tests du `sessionPosteStore` — **mode poste persistant** (E04US001, correctif D-1/D-2).
//
// Garde-fou du contrat qui distingue « ce navigateur est un poste » (intention persistante) de la
// simple présence d'un jeton : une session **révoquée** doit laisser la tablette sur le
// **rattachement**, jamais la renvoyer vers l'admin (D-13) ; seul un **détachement explicite**
// quitte le mode poste, et le thème survit aux deux. ⚠️ Sous jsdom global (ADR-0053), la garde SSR
// `typeof document` d'`appliquerTheme` ne protège plus que le vrai rendu serveur, pas ces tests.

import { beforeEach, describe, expect, it } from 'vitest'
import { useSessionPosteStore, type PosteRattache } from './sessionPosteStore'

// Depuis E07US004, un poste porte sa **nature** : le même rattachement mène à une tablette de cible
// ou à un écran de salle. Les invariants testés ici (mode poste persistant, révocation, thème) sont
// communs aux deux — c'est même la raison d'avoir gardé un seul flux plutôt que deux.
const cible: PosteRattache = { tournoi_id: 1, type: 'cible', cible_index: 3, libelle: null }

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
