// Tests de `resoudreRole` — précédence de l'aiguillage d'entrée (E00US017, ADR-0042).
//
// Le garde-fou du contrat : une **session en cours prime** sur le choix (jamais retomber sur l'écran
// de choix après un rechargement), le **poste est un verrou physique** (D-13, inconditionnel), et les
// jetons hérités (admin/scoreur) ne servent qu'à **ne pas rejouer** le choix pour une session
// préexistante — jamais à contredire un choix explicite. Chaque cas dérive de la table de l'ADR.

import { describe, expect, it } from 'vitest'
import { resoudreRole, type EtatEntree } from './resoudreRole'

// Appareil neuf : aucun jeton, aucun choix.
const vierge: EtatEntree = {
  roleChoisi: null,
  estPoste: false,
  codePosteUrl: false,
  aJetonAdmin: false,
  aJetonScoreur: false,
}

describe('resoudreRole — précédence de l’aiguillage d’entrée', () => {
  it('appareil vierge → écran de choix (null)', () => {
    expect(resoudreRole(vierge)).toBeNull()
  })

  it('chaque choix explicite est servi tel quel', () => {
    expect(resoudreRole({ ...vierge, roleChoisi: 'public' })).toBe('public')
    expect(resoudreRole({ ...vierge, roleChoisi: 'scoreur' })).toBe('scoreur')
    expect(resoudreRole({ ...vierge, roleChoisi: 'admin' })).toBe('admin')
    expect(resoudreRole({ ...vierge, roleChoisi: 'tablette' })).toBe('tablette')
  })

  it('un poste rattaché est tablette, même sans choix (verrou physique D-13)', () => {
    expect(resoudreRole({ ...vierge, estPoste: true })).toBe('tablette')
  })

  it('une arrivée par le QR (?poste=) est tablette, même sans choix', () => {
    expect(resoudreRole({ ...vierge, codePosteUrl: true })).toBe('tablette')
  })

  it('le poste prime sur tout autre choix explicite (D-13 inconditionnel)', () => {
    // Cas limite : un marqueur « public » traîne mais l'appareil est physiquement un poste → tablette.
    expect(resoudreRole({ ...vierge, roleChoisi: 'public', estPoste: true })).toBe('tablette')
  })

  it('un jeton admin hérité (sans choix) → admin, pour ne pas rejouer le choix (rétro-compat)', () => {
    expect(resoudreRole({ ...vierge, aJetonAdmin: true })).toBe('admin')
  })

  it('un jeton scoreur hérité (sans choix) → scoreur (rétro-compat)', () => {
    expect(resoudreRole({ ...vierge, aJetonScoreur: true })).toBe('scoreur')
  })

  it('le choix explicite prime sur un jeton hérité (l’inférence n’est qu’un repli)', () => {
    // Priorité à l'intention déclarée : le marqueur passe avant l'inférence par jeton.
    expect(resoudreRole({ ...vierge, roleChoisi: 'public', aJetonAdmin: true })).toBe('public')
  })

  it('admin prime sur scoreur quand les deux jetons traînent sans choix', () => {
    expect(resoudreRole({ ...vierge, aJetonAdmin: true, aJetonScoreur: true })).toBe('admin')
  })

  it('le choix explicite prime AUSSI sur un jeton scoreur hérité (symétrie du cas admin)', () => {
    expect(resoudreRole({ ...vierge, roleChoisi: 'public', aJetonScoreur: true })).toBe('public')
  })

  it('le verrou poste prime sur un jeton admin résiduel (ex-admin sur tablette rattachée → tablette)', () => {
    expect(resoudreRole({ ...vierge, estPoste: true, aJetonAdmin: true })).toBe('tablette')
  })

  it('une arrivée par QR prime sur un choix admin mémorisé (le QR est le choix, D-13)', () => {
    expect(resoudreRole({ ...vierge, codePosteUrl: true, roleChoisi: 'admin' })).toBe('tablette')
  })
})
