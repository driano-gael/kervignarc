// Le modèle du réglage de Big Shoot Off (E05US028) — logique pure, aucun DOM.
//
// ⚠️ **Ce que ces tests gardent vraiment, c'est un miroir.** `paliers` recopie la règle de
// `ConfigurationBigShootOff.paliers_pour` (côté serveur, qui fait autorité). Le miroir existe parce
// que l'atelier compose aussi des **formats de bibliothèque**, sans tournoi — il n'y a donc aucune
// route à interroger. Sa dérive ne produirait qu'un aperçu faux, jamais un tournoi faux ; mais un
// aperçu faux se lit comme une promesse, donc il se garde.

import { describe, expect, it } from 'vitest'

import {
  BIG_SHOOT_OFF_PAR_DEFAUT,
  decrireProjection,
  depuisReglage,
  estValide,
  lireSortants,
  paliers,
  versReglage,
} from './bigShootOff'

describe('lireSortants', () => {
  it('lit une liste séparée par des virgules', () => {
    expect(lireSortants('4, 2, 1')).toEqual([4, 2, 1])
  })

  it('tolère les séparateurs que l’organisateur tape réellement', () => {
    // Aide à la saisie, pas format à respecter : espaces, points-virgules, virgules mêlés.
    expect(lireSortants('4 2;1')).toEqual([4, 2, 1])
  })

  it('refuse une case à zéro plutôt que de la filtrer en silence', () => {
    // « 4, 0, 1 » décrirait une manche qu'on ferait tirer pour rien — l'organisateur voulait
    // « 4, 1 ». Filtrer changerait sa liste sans le lui dire.
    expect(lireSortants('4, 0, 1')).toBeUndefined()
  })

  it('refuse une liste vide : une phase qui n’élimine personne est un échauffement', () => {
    expect(lireSortants('   ')).toBeUndefined()
  })

  it('refuse une case illisible', () => {
    expect(lireSortants('4, deux')).toBeUndefined()
  })
})

describe('paliers', () => {
  it('déroule la liste quand l’effectif la porte', () => {
    expect(paliers(12, [4, 2, 1])).toEqual([8, 6, 5])
  })

  it('écourte à la première manche qui viderait le pas de tir', () => {
    // 6 archers, `[4, 2, 1]` : la manche 1 en sort 4 (il reste 2), la manche 2 en sortirait 2 sur
    // 2 — il ne resterait personne. C'est la règle « on joue tant que la manche est possible », qui
    // rend un format réutilisable sur un effectif qu'il ignore.
    expect(paliers(6, [4, 2, 1])).toEqual([2])
  })

  it('ne prolonge pas la liste toute seule jusqu’au vainqueur unique', () => {
    // 20 entrants laissent 13 rescapés : ce n'est probablement pas voulu, et c'est **exactement**
    // pourquoi la projection est affichée. Le moteur montre, il ne décide pas à la place.
    expect(paliers(20, [4, 2, 1])).toEqual([16, 14, 13])
  })

  it('rend une liste vide sur un effectif illisible plutôt qu’un aperçu inventé', () => {
    expect(paliers(0, [1])).toEqual([])
  })
})

describe('decrireProjection', () => {
  it('dit le chemin et le nombre de rescapés', () => {
    expect(decrireProjection(12, [4, 2, 1])).toBe('12 → 8 → 6 → 5 : 5 rescapés.')
  })

  it('nomme les manches qui ne se joueront pas', () => {
    // La contrepartie honnête de « on joue tant que la manche est possible » : l'organisateur ne
    // doit pas croire jouer une liste qu'il ne joue pas.
    expect(decrireProjection(6, [4, 2, 1])).toContain('ne se joueront pas')
  })

  it('le dit aussi quand aucune manche n’est jouable', () => {
    expect(decrireProjection(2, [4])).toContain('aucune manche jouable')
  })
})

describe('versReglage', () => {
  it('convertit un état d’écran en ce qui part au serveur', () => {
    expect(
      versReglage({
        sortants: '4, 2, 1',
        volees: '2',
        fleches: '3',
        cumul: true,
        departageSortants: true,
      }),
    ).toEqual({
      eliminations: [4, 2, 1],
      volees: 2,
      fleches_par_volee: 3,
      cumul_des_manches: true,
      departage_les_sortants: true,
    })
  })

  it('rend `undefined` sur une saisie illisible — « illisible », pas « efface »', () => {
    expect(versReglage({ ...BIG_SHOOT_OFF_PAR_DEFAUT, sortants: '' })).toBeUndefined()
    expect(estValide({ ...BIG_SHOOT_OFF_PAR_DEFAUT, volees: '0' })).toBe(false)
  })
})

describe('depuisReglage', () => {
  it('retombe sur le défaut quand la phase n’est pas réglée', () => {
    // `null` est licite : le type se choisit **avant** ses paramètres.
    expect(depuisReglage(null)).toEqual(BIG_SHOOT_OFF_PAR_DEFAUT)
  })

  it('fait l’aller-retour sans perte', () => {
    const reglage = {
      eliminations: [4, 2, 1],
      volees: 2,
      fleches_par_volee: 6,
      cumul_des_manches: true,
      departage_les_sortants: false,
    }
    expect(versReglage(depuisReglage(reglage))).toEqual(reglage)
  })
})
