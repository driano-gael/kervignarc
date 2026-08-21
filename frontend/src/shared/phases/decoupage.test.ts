// Tests du modèle du **découpage d'une qualification en tours** (E05US035, ADR-0093).
//
// Dérivés du CA : « une qualification se règle en `n` tours à l'atelier ». Ce qui se joue ici est la
// conversion « ce que l'écran affiche ↔ ce qui part au serveur », plus la phrase qui annonce ce que
// le réglage donne. L'autorité sur la divisibilité reste le domaine ; ce miroir sert à **le dire**
// avant le refus, pas à décider à sa place.

import { describe, expect, it } from 'vitest'

import {
  DECOUPAGE_PAR_DEFAUT,
  TOURS_MAX_REGLABLES,
  decrireDecoupage,
  depuisDecoupage,
  estValide,
  versDecoupage,
} from './decoupage'

describe('conversion état ↔ réglage', () => {
  it('repart du défaut quand la phase n’est pas découpée', () => {
    expect(depuisDecoupage(null)).toEqual(DECOUPAGE_PAR_DEFAUT)
  })

  it('relit le nombre de tours posé', () => {
    expect(depuisDecoupage({ nb_tours: 2 })).toEqual({ tours: '2' })
  })

  it('rend le réglage pour un découpage réel', () => {
    expect(versDecoupage({ tours: '2' })).toEqual({ nb_tours: 2 })
  })

  it('rend `null` — et non un découpage à 1 — pour un seul tour', () => {
    // ⚠️ La nuance n'est pas cosmétique : « non découpée » est l'état par défaut de toute
    // qualification existante. Persister `{ nb_tours: 1 }` ferait apparaître un réglage là où
    // l'organisateur n'a rien réglé, et rendrait la relecture d'une base ancienne différente de
    // celle d'une base neuve pour un comportement identique.
    expect(versDecoupage({ tours: '1' })).toBeNull()
  })

  it('rend `undefined` — « illisible », jamais « efface » — sur une saisie inexploitable', () => {
    expect(versDecoupage({ tours: '' })).toBeUndefined()
    expect(versDecoupage({ tours: 'deux' })).toBeUndefined()
    expect(versDecoupage({ tours: '1.5' })).toBeUndefined()
    expect(versDecoupage({ tours: '0' })).toBeUndefined()
    expect(versDecoupage({ tours: String(TOURS_MAX_REGLABLES + 1) })).toBeUndefined()
  })

  it('ne bloque la soumission que sur l’illisible', () => {
    expect(estValide({ tours: '2' })).toBe(true)
    expect(estValide({ tours: '1' })).toBe(true)
    expect(estValide({ tours: '' })).toBe(false)
  })
})

describe('ce que le découpage donne, dit avant le refus', () => {
  it('annonce la longueur obtenue', () => {
    expect(decrireDecoupage(20, 2)).toBe('2 tours de 10 volées.')
  })

  it('accorde le singulier sur un tour d’une seule volée', () => {
    expect(decrireDecoupage(4, 4)).toBe('4 tours de 1 volée.')
  })

  it('nomme l’écart quand le découpage ne tombe pas juste', () => {
    // C'est tout l'objet du miroir : le domaine refuse déjà, mais l'organisateur ne le
    // découvrirait qu'au 422, une fois l'étape entière soumise.
    expect(decrireDecoupage(20, 3)).toContain('ne se découpent pas en 3 tours égaux')
  })

  it('dit qu’aucune pause ne peut se poser sur une qualification d’un seul bloc', () => {
    expect(decrireDecoupage(20, 1)).toContain('aucune pause')
  })

  it('ne promet aucune longueur quand le barème est inconnu', () => {
    // Le cas de l'atelier : un format de bibliothèque s'écrit sans connaître le barème du tournoi
    // qui l'appliquera. Inventer un dénominateur serait pire que de ne rien dire.
    expect(decrireDecoupage(null, 2)).toContain('dépend du barème')
  })
})
