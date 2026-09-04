// Lecture et effacement du code de scoreur porté par le QR (E16US015, ADR-0105).
//
// Adossée à `window.location`, mais c'est elle qui décide si l'arrivée par QR ouvre une session —
// et elle porte une exigence de sécurité : le code ne reste ni dans l'adresse, ni dans l'historique.

import { beforeEach, describe, expect, it } from 'vitest'
import { codeScoreurDepuisUrl, oublierCodeScoreurUrl } from './url'

function placerUrl(url: string) {
  window.history.replaceState(null, '', url)
}

describe('codeScoreurDepuisUrl', () => {
  beforeEach(() => placerUrl('/scoreur'))

  it('rend le code quand le QR en porte un', () => {
    placerUrl('/scoreur#code=AB12CD')
    expect(codeScoreurDepuisUrl()).toBe('AB12CD')
  })

  it('rend null hors arrivée par QR', () => {
    expect(codeScoreurDepuisUrl()).toBeNull()
  })

  it('ignore un `?code=` en query — le contrat est le fragment', () => {
    // Le fragment n'est jamais envoyé au serveur ; une query le serait, et finirait dans le
    // journal d'accès d'uvicorn puis dans le `Referer` de chaque sous-ressource.
    placerUrl('/scoreur?code=AB12CD')
    expect(codeScoreurDepuisUrl()).toBeNull()
  })

  it('distingue un paramètre présent mais vide d’un paramètre absent', () => {
    placerUrl('/scoreur#code=')
    expect(codeScoreurDepuisUrl()).toBe('')
  })
})

describe('oublierCodeScoreurUrl', () => {
  beforeEach(() => placerUrl('/scoreur'))

  it('retire le code en gardant le chemin du monde', () => {
    placerUrl('/scoreur#code=AB12CD')

    oublierCodeScoreurUrl()

    expect(window.location.pathname).toBe('/scoreur')
    expect(window.location.hash).toBe('')
    expect(codeScoreurDepuisUrl()).toBeNull()
  })

  it('laisse la query intacte — elle porte le `?poste=` du QR de cible', () => {
    // ⚠️ Cette fonction s'exécute au shell, donc AUSSI sur l'adresse d'une tablette rattachée :
    // vider la query y casserait le rattachement de la cible (`features/poste/url.ts`).
    placerUrl('/cible?poste=ZZZ999#code=AB12CD')

    oublierCodeScoreurUrl()

    expect(window.location.search).toBe('?poste=ZZZ999')
    expect(window.location.hash).toBe('')
  })

  it('laisse le reste du fragment intact', () => {
    placerUrl('/scoreur#code=AB12CD&onglet=duels')

    oublierCodeScoreurUrl()

    expect(window.location.hash).toBe('#onglet=duels')
  })
})
