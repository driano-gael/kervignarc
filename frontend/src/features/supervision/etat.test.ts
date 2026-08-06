// Tests de la dérivation d'affichage d'un poste (E12US001) — les trois états et le libellé
// d'avancement. Calqué sur `shared/realtime/indicateur.test.ts` : logique pure, testée en node.

import { describe, expect, it } from 'vitest'
import { afficheEtat, avancementLibelle, fractionAvancement, voleeCourte } from './etat'

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

  it('cible sans aucun archer placé (volee_courante 0) → tiret, pas « volée 0/12 »', () => {
    expect(avancementLibelle({ volee_courante: 0, nb_volees: 12 })).toBe('—')
  })
})

// — Tuile de supervision (E17US004, planche A13 variante B « grille de tuiles »).
//
// Les deux dérivations que la tuile ajoute au tableau. Elles partagent avec `avancementLibelle` la
// même définition de « avancement situable » : c'est l'invariant à ne pas casser, sinon une tuile
// afficherait une jauge là où le tableau affiche « — ».

describe('voleeCourte — le « v8 » de la tuile', () => {
  it('rend la volée en cours en forme courte', () => {
    expect(voleeCourte({ volee_courante: 8, nb_volees: 12 })).toBe('v8')
  })

  it.each([
    ['pas de grille', null],
    ['qualification non configurée', { volee_courante: 3, nb_volees: 0 }],
    ['aucun archer placé', { volee_courante: 0, nb_volees: 12 }],
  ])('rien à afficher quand l’avancement n’est pas situable — %s', (_cas, avancement) => {
    expect(voleeCourte(avancement)).toBeNull()
  })

  it('reste cohérent avec le libellé long du tableau', () => {
    // Le jour où l'un rend une valeur et l'autre « — », la tuile et le tableau se contredisent sur
    // le même poste, au même instant, sur le même écran.
    const sansSens = { volee_courante: 0, nb_volees: 12 }
    expect(voleeCourte(sansSens)).toBeNull()
    expect(avancementLibelle(sansSens)).toBe('—')
  })
})

describe('fractionAvancement — le remplissage de la jauge', () => {
  it('rend la part de la grille déjà tirée', () => {
    expect(fractionAvancement({ volee_courante: 6, nb_volees: 12 })).toBe(0.5)
  })

  it('vaut 1 sur une grille terminée', () => {
    expect(fractionAvancement({ volee_courante: 12, nb_volees: 12 })).toBe(1)
  })

  it('borne à 1 une volée courante au-delà de la grille, pour ne pas déborder de la piste', () => {
    expect(fractionAvancement({ volee_courante: 14, nb_volees: 12 })).toBe(1)
  })

  it('ne rend rien quand l’avancement n’est pas situable', () => {
    expect(fractionAvancement(null)).toBeNull()
    expect(fractionAvancement({ volee_courante: 0, nb_volees: 12 })).toBeNull()
  })
})
