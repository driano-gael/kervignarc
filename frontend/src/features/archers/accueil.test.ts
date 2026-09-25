// A09 · inscriptions — variante retenue au questionnaire du 04/08 : « B — Recherche d'abord, liste
// ensuite » (« elle ne doit pas polluer le reste de l'écran »). La planche : un champ, puis quatre
// compteurs d'entrée — inscrits, non placés, non réglés, doublons. E17US007.

import { describe, expect, it } from 'vitest'
import type { Archer } from './api'
import { archersAffiches, compteurs, type Ensembles } from './accueil'

const archer = (id: number, nom: string, prenom = 'Luc'): Archer => ({ id, nom, prenom }) as Archer

const TOUS = [archer(1, 'MARTIN'), archer(2, 'Durand'), archer(3, 'Hélias', 'Élodie')]
const ENSEMBLES: Ensembles = {
  nonPlaces: new Set([2]),
  nonRegles: new Set([1, 2]),
  doublons: new Set([3]),
}
const ids = (liste: Archer[]) => liste.map((a) => a.id)

describe('archersAffiches — recherche d’abord', () => {
  it('sans recherche ni compteur choisi, rien n’est listé', () => {
    expect(archersAffiches(TOUS, { requete: '', filtre: null, ouvert: null }, ENSEMBLES)).toEqual(
      [],
    )
  })

  it('la recherche filtre par nom ou prénom, sans accents ni casse', () => {
    expect(
      ids(archersAffiches(TOUS, { requete: 'helias', filtre: null, ouvert: null }, ENSEMBLES)),
    ).toEqual([3])
    expect(
      ids(archersAffiches(TOUS, { requete: 'elodie', filtre: null, ouvert: null }, ENSEMBLES)),
    ).toEqual([3])
  })

  it('un compteur choisi liste sa population', () => {
    const avec = (filtre: 'tous' | 'non_places' | 'non_regles' | 'doublons') =>
      ids(archersAffiches(TOUS, { requete: '', filtre, ouvert: null }, ENSEMBLES))
    expect(avec('tous')).toEqual([1, 2, 3])
    expect(avec('non_places')).toEqual([2])
    expect(avec('non_regles')).toEqual([1, 2])
    expect(avec('doublons')).toEqual([3])
  })

  it('compteur et recherche se combinent', () => {
    expect(
      ids(archersAffiches(TOUS, { requete: 'dur', filtre: 'non_regles', ouvert: null }, ENSEMBLES)),
    ).toEqual([2])
  })

  it('une fiche ouverte par son adresse reste visible, même hors du filtre', () => {
    // La recherche transverse (E16US010) ouvre une fiche par l'adresse : l'écran vide ne doit pas
    // la cacher, sinon le résultat cliqué ne mène nulle part.
    expect(ids(archersAffiches(TOUS, { requete: '', filtre: null, ouvert: 3 }, ENSEMBLES))).toEqual(
      [3],
    )
    expect(
      ids(archersAffiches(TOUS, { requete: 'martin', filtre: null, ouvert: 3 }, ENSEMBLES)),
    ).toEqual([1, 3])
  })

  it('une population inconnue (plans illisibles) ne liste rien, plutôt qu’un faux « aucun »', () => {
    const inconnu = { ...ENSEMBLES, nonPlaces: null }
    expect(
      archersAffiches(TOUS, { requete: '', filtre: 'non_places', ouvert: null }, inconnu),
    ).toEqual([])
  })
})

describe('compteurs', () => {
  it('compte chaque population parmi les inscrits', () => {
    expect(compteurs(TOUS, ENSEMBLES)).toEqual({
      inscrits: 3,
      nonPlaces: 1,
      nonRegles: 2,
      doublons: 1,
    })
  })

  it('un identifiant absent des inscrits n’est pas compté (archer désinscrit, lecture en retard)', () => {
    const decale = { ...ENSEMBLES, nonRegles: new Set([1, 99]) }
    expect(compteurs(TOUS, decale).nonRegles).toBe(1)
  })

  it('une population inconnue reste inconnue — `null`, jamais 0', () => {
    expect(compteurs(TOUS, { ...ENSEMBLES, nonPlaces: null }).nonPlaces).toBeNull()
  })
})
