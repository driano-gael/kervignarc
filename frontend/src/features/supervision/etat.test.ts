// Tests de la dérivation d'affichage d'un poste (E12US001) — les trois états et le libellé
// d'avancement. Calqué sur `shared/realtime/indicateur.test.ts` : logique pure, testée en node.

import { describe, expect, it } from 'vitest'
import { afficheEtat, avancementLibelle } from './etat'

describe('afficheEtat', () => {
  it('en ligne → pastille ok + « En ligne »', () => {
    expect(afficheEtat('en_ligne')).toEqual({ classe: 'en_ligne', libelle: 'En ligne' })
  })

  it('hors ligne → « Hors ligne » (rendu en ambre côté CSS, pas rouge — DV-03)', () => {
    expect(afficheEtat('hors_ligne')).toEqual({ classe: 'hors_ligne', libelle: 'Hors ligne' })
  })

  it('non rattaché → troisième état, neutre', () => {
    expect(afficheEtat('non_rattache')).toEqual({
      classe: 'non_rattache',
      libelle: 'Non rattaché',
    })
  })
})

describe('avancementLibelle', () => {
  it('un poste en saisie → « volée 8/12 »', () => {
    expect(avancementLibelle({ volee_courante: 8, nb_volees: 12 })).toBe('volée 8/12')
  })

  it('pas de grille (avancement nul) → tiret', () => {
    expect(avancementLibelle(null)).toBe('—')
  })

  it('qualification pas configurée (nb_volees 0) → tiret, pas « volée 0/0 »', () => {
    expect(avancementLibelle({ volee_courante: 0, nb_volees: 0 })).toBe('—')
  })
})
