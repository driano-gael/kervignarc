// Tests du routeur maison (E14US003). Partie **pure** : aucune dépendance au DOM.

import { describe, expect, it } from 'vitest'
import { analyserChemin, construireChemin, mondeDuRole, roleDuMonde, type Route } from './routeur'

describe('analyserChemin', () => {
  it('la racine ouvre l’écran de choix des quatre portes', () => {
    expect(analyserChemin('/')).toEqual({ monde: 'accueil', segments: [] })
    expect(analyserChemin('')).toEqual({ monde: 'accueil', segments: [] })
  })

  it.each([
    ['/public', 'public'],
    ['/scoreur', 'scoreur'],
    ['/cible', 'tablette'],
    ['/admin', 'admin'],
  ] as const)('%s ouvre le monde %s', (chemin, monde) => {
    expect(analyserChemin(chemin)).toEqual({ monde, segments: [] })
  })

  it('l’adresse dit « cible » là où le code dit « tablette » (règle 3 : le bénévole lit du FFTA)', () => {
    expect(analyserChemin('/cible').monde).toBe('tablette')
    // Et l'inverse n'existe pas : `/tablette` n'est pas une adresse du produit.
    expect(analyserChemin('/tablette').monde).toBe('accueil')
  })

  it('les segments suivants sont rendus tels quels, sans être interprétés', () => {
    expect(analyserChemin('/admin/pilotage/supervision')).toEqual({
      monde: 'admin',
      segments: ['pilotage', 'supervision'],
    })
  })

  it('tolère les barres surnuméraires ou finales', () => {
    expect(analyserChemin('/admin//pilotage/')).toEqual({
      monde: 'admin',
      segments: ['pilotage'],
    })
  })

  it('un chemin inconnu retombe sur l’accueil, jamais sur un cul-de-sac', () => {
    // Le jour J, un bénévole qui tape mal une adresse doit voir les quatre portes.
    expect(analyserChemin('/inconnu/profond')).toEqual({ monde: 'accueil', segments: [] })
  })
})

const CAS_CONSTRUCTION: [Route, string][] = [
  [{ monde: 'accueil', segments: [] }, '/'],
  [{ monde: 'public', segments: [] }, '/public'],
  [{ monde: 'tablette', segments: [] }, '/cible'],
  [{ monde: 'admin', segments: ['gestion', 'inscriptions'] }, '/admin/gestion/inscriptions'],
]

describe('construireChemin', () => {
  it.each(CAS_CONSTRUCTION)('%o → %s', (route, attendu) => {
    expect(construireChemin(route)).toBe(attendu)
  })

  it('est la réciproque exacte d’analyserChemin sur les chemins connus', () => {
    for (const chemin of [
      '/',
      '/public',
      '/scoreur',
      '/cible',
      '/admin',
      '/admin/atelier/blasons',
    ]) {
      expect(construireChemin(analyserChemin(chemin))).toBe(chemin)
    }
  })
})

describe('correspondance monde ↔ rôle', () => {
  it('l’accueil n’est pas un rôle : c’est l’absence de choix', () => {
    expect(roleDuMonde('accueil')).toBeNull()
  })

  it('les quatre autres mondes sont exactement les quatre rôles', () => {
    for (const role of ['tablette', 'public', 'scoreur', 'admin'] as const) {
      expect(roleDuMonde(mondeDuRole(role))).toBe(role)
    }
  })
})
