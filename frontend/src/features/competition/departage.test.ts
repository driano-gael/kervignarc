// Tests des ex æquo du classement (retour maquettes du 04/08/2026, A16).
// Dérivés de la réponse — « la règle de départage : seulement en cas d'ex aequo » — et de la règle
// FFTA déjà documentée (`referentiel-ffta` §8.1), pas de la lecture de l'implémentation.

import { describe, expect, it } from 'vitest'
import { aDesExAequo, estExAequo, totauxExAequo, type LigneDepartageable } from './departage'

function ligne(total: number, categorie_id = 1, statut = 'en_lice'): LigneDepartageable {
  return { total, categorie_id, statut }
}

describe('totauxExAequo', () => {
  it('un classement sans égalité n’en signale aucune', () => {
    expect(aDesExAequo(totauxExAequo([ligne(280), ligne(275), ligne(270)]))).toBe(false)
  })

  it('deux archers au même total, même catégorie : ex æquo', () => {
    const egalites = totauxExAequo([ligne(280), ligne(280), ligne(270)])
    expect(aDesExAequo(egalites)).toBe(true)
    expect(estExAequo(ligne(280), egalites)).toBe(true)
    expect(estExAequo(ligne(270), egalites)).toBe(false)
  })

  it('même total dans **deux catégories différentes** : pas d’ex æquo', () => {
    // Ils ne se disputent rien : le classement qui compte pour un archer est celui de sa catégorie.
    const egalites = totauxExAequo([ligne(280, 1), ligne(280, 2)])
    expect(aDesExAequo(egalites)).toBe(false)
  })

  it('un abandon au même total ne crée pas d’égalité', () => {
    // Son score reste affiché, mais il n'est plus classé : signaler un départage qui n'aura jamais
    // lieu serait un faux signal (ADR-0050).
    const egalites = totauxExAequo([ligne(280), ligne(280, 1, 'abandon')])
    expect(aDesExAequo(egalites)).toBe(false)
  })

  it('deux archers disqualifiés au même total ne sont pas ex æquo entre eux non plus', () => {
    const egalites = totauxExAequo([
      ligne(280, 1, 'disqualifie'),
      ligne(280, 1, 'disqualifie'),
      ligne(270),
    ])
    expect(aDesExAequo(egalites)).toBe(false)
  })

  it('trois archers au même total forment une seule égalité', () => {
    const egalites = totauxExAequo([ligne(280), ligne(280), ligne(280)])
    expect(egalites.get(1)).toEqual(new Set([280]))
  })

  it('plusieurs égalités, dans plusieurs catégories', () => {
    const egalites = totauxExAequo([
      ligne(280, 1),
      ligne(280, 1),
      ligne(250, 1),
      ligne(300, 2),
      ligne(300, 2),
    ])
    expect(egalites.get(1)).toEqual(new Set([280]))
    expect(egalites.get(2)).toEqual(new Set([300]))
  })

  it('un classement vide ne plante pas', () => {
    expect(aDesExAequo(totauxExAequo([]))).toBe(false)
  })
})
