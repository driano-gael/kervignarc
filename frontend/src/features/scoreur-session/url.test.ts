// Lecture et effacement du code de scoreur porté par l'URL du QR (E16US015).
//
// Logique **pure côté décision**, mais adossée à `window.location` : on la verrouille ici parce que
// c'est elle qui décide si l'arrivée par QR ouvre une session — et parce qu'elle porte une exigence
// de sécurité (le code ne reste pas dans la barre d'adresse).

import { beforeEach, describe, expect, it } from 'vitest'
import { codeScoreurDepuisUrl, oublierCodeScoreurUrl } from './url'

function placerUrl(url: string) {
  window.history.replaceState(null, '', url)
}

describe('codeScoreurDepuisUrl', () => {
  beforeEach(() => placerUrl('/scoreur'))

  it('rend le code quand le QR en porte un', () => {
    placerUrl('/scoreur?code=AB12CD')
    expect(codeScoreurDepuisUrl()).toBe('AB12CD')
  })

  it('rend null hors arrivée par QR', () => {
    expect(codeScoreurDepuisUrl()).toBeNull()
  })

  it('distingue un paramètre présent mais vide d’un paramètre absent', () => {
    placerUrl('/scoreur?code=')
    expect(codeScoreurDepuisUrl()).toBe('')
  })
})

describe('oublierCodeScoreurUrl', () => {
  it('retire le code de la barre d’adresse en gardant le chemin du monde', () => {
    placerUrl('/scoreur?code=AB12CD')

    oublierCodeScoreurUrl()

    expect(window.location.pathname).toBe('/scoreur')
    expect(window.location.search).toBe('')
    expect(codeScoreurDepuisUrl()).toBeNull()
  })
})
