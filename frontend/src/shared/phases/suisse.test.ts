// Le modèle du réglage de système suisse (E05US030) — logique pure, aucun DOM.
//
// ⚠️ **Ce que ces tests gardent, c'est un miroir** : `rondesMaximales` recopie
// `domain/suisse.py::rondes_maximales`, qui fait autorité. Le miroir existe parce que l'atelier
// compose aussi des formats de **bibliothèque**, sans tournoi — il n'y a aucune route à interroger.
// Sa dérive ne produirait qu'un avertissement faux, jamais un tournoi faux ; mais un avertissement
// faux se lit comme une promesse, donc il se garde.

import { describe, expect, it } from 'vitest'

import {
  SUISSE_PAR_DEFAUT,
  decrireBorne,
  depuisReglage,
  estValide,
  rondesMaximales,
  versReglage,
} from './suisse'

describe('versReglage', () => {
  it('rend le nombre de rondes saisi', () => {
    expect(versReglage({ rondes: '7' })).toEqual({ nb_rondes: 7 })
  })

  it('refuse un champ vide sans l’effacer pour autant', () => {
    // `undefined` veut dire « illisible », pas « efface » : l'appelant bloque sa soumission.
    expect(versReglage({ rondes: '' })).toBeUndefined()
    expect(versReglage({ rondes: '  ' })).toBeUndefined()
  })

  it('refuse zéro, le négatif et le non entier', () => {
    expect(versReglage({ rondes: '0' })).toBeUndefined()
    expect(versReglage({ rondes: '-2' })).toBeUndefined()
    expect(versReglage({ rondes: '2,5' })).toBeUndefined()
  })

  it('refuse au-delà de ce que l’API accepte', () => {
    // `ReglageSuisseDTO.nb_rondes` est borné à 64 : mieux vaut le dire ici qu'encaisser un 422.
    expect(versReglage({ rondes: '64' })).toEqual({ nb_rondes: 64 })
    expect(versReglage({ rondes: '65' })).toBeUndefined()
  })
})

describe('depuisReglage', () => {
  it('retombe sur le défaut quand la phase n’est pas réglée', () => {
    expect(depuisReglage(null)).toEqual(SUISSE_PAR_DEFAUT)
  })

  it('relit ce que porte la phase', () => {
    expect(depuisReglage({ nb_rondes: 3 })).toEqual({ rondes: '3' })
  })

  it('fait l’aller-retour sans perte', () => {
    expect(versReglage(depuisReglage({ nb_rondes: 9 }))).toEqual({ nb_rondes: 9 })
  })
})

describe('estValide', () => {
  it('suit versReglage', () => {
    expect(estValide({ rondes: '5' })).toBe(true)
    expect(estValide({ rondes: '' })).toBe(false)
  })
})

describe('rondesMaximales', () => {
  it('rend n-1 à effectif pair', () => {
    // Chacun a n-1 adversaires et joue à chaque ronde.
    expect(rondesMaximales(4)).toBe(3)
    expect(rondesMaximales(16)).toBe(15)
  })

  it('rend n à effectif impair — le bye tourne, c’est un tour de plus', () => {
    // ⚠️ Le raccourci « n-1 dans les deux cas » refuserait une composition jouable.
    expect(rondesMaximales(5)).toBe(5)
    expect(rondesMaximales(9)).toBe(9)
  })

  it('rend 0 sous deux tireurs', () => {
    expect(rondesMaximales(1)).toBe(0)
    expect(rondesMaximales(0)).toBe(0)
  })
})

describe('decrireBorne', () => {
  it('dit la borne en clair — c’est le CA', () => {
    expect(decrireBorne(8, 5)).toBe(
      '8 archers : 7 rondes au maximum sans que deux archers se rencontrent deux fois.',
    )
  })

  it('nomme l’écart quand le réglage dépasse la borne', () => {
    // Le service **borne à la lecture** : sans cette phrase, l'organisateur croit jouer 5 rondes et
    // en voit 3 le jour J, sans qu'aucun refus ne le prévienne.
    expect(decrireBorne(4, 5)).toBe(
      '4 archers : 3 rondes au maximum sans que deux archers se rencontrent deux fois. ' +
        'Vous en avez réglé 5 : les 3 premières seront jouées.',
    )
  })

  it('reste juste au singulier', () => {
    expect(decrireBorne(2, 4)).toBe(
      '2 archers : 1 ronde au maximum sans que deux archers se rencontrent deux fois. ' +
        'Vous en avez réglé 4 : une seule sera jouée.',
    )
  })

  it('ne promet rien sur un effectif trop mince', () => {
    expect(decrireBorne(1, 5)).toBe(
      '1 archer : aucune ronde n’est appariable (il en faut au moins deux).',
    )
    expect(decrireBorne(0, 5)).toBe(
      '0 archer : aucune ronde n’est appariable (il en faut au moins deux).',
    )
  })
})
