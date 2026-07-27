// Tests de la logique pure de la saisie en duels (E04US013) — libellés, avancement, statut, injection
// optimiste. Le serveur reste l'autorité (résultat, mode, zones) ; on teste ce qui pilote l'affichage.

import { describe, expect, it } from 'vitest'
import type { Duel, SaisirBarrage, SaisirManche } from './api'
import {
  injecterBarrage,
  injecterManche,
  libelleMode,
  libelleTour,
  mancheExistante,
  prochaineMancheASaisir,
  statutDuel,
  totalVolee,
} from './duel'

function duel(over: Partial<Duel> = {}): Duel {
  return {
    numero: 1,
    tour: 1,
    place_en_jeu: null,
    haut: { archer_id: 1, nom: 'DUPONT', prenom: 'Jean' },
    bas: { archer_id: 2, nom: 'MARTIN', prenom: 'Luc' },
    est_bye: false,
    mode: 'sets',
    nb_manches: 5,
    nb_fleches_par_volee: 3,
    points_pour_gagner: 6,
    zones: ['10', '9', '8', '7', '6', 'M'],
    validee_par: null,
    manches: [],
    barrage: null,
    resultat: null,
    ...over,
  }
}

describe('libelleMode', () => {
  it('distingue sets, cumul (poulies) et absence de mode', () => {
    expect(libelleMode('sets')).toBe('Système de sets')
    expect(libelleMode('cumul')).toBe('Cumul (arc à poulies)')
    expect(libelleMode(null)).toBe('')
  })
})

describe('libelleTour', () => {
  it('nomme le tour par distance à la finale', () => {
    expect(libelleTour({ tour: 2, place_en_jeu: [1, 2] }, 2)).toBe('Finale')
    expect(libelleTour({ tour: 1, place_en_jeu: null }, 2)).toBe('Demi-finales')
    expect(libelleTour({ tour: 1, place_en_jeu: null }, 3)).toBe('Quarts de finale')
    expect(libelleTour({ tour: 1, place_en_jeu: null }, 4)).toBe('1/8 de finale')
  })

  it('distingue la petite finale (3ᵉ place) de la finale, même tour', () => {
    expect(libelleTour({ tour: 2, place_en_jeu: [3, 4] }, 2)).toBe('Petite finale (3ᵉ place)')
  })
})

describe('prochaineMancheASaisir', () => {
  it('la plus petite manche non encore saisie', () => {
    expect(prochaineMancheASaisir({ manches: [] }, 5)).toBe(1)
    expect(prochaineMancheASaisir({ manches: [{ numero: 1, haut: [], bas: [] }] }, 5)).toBe(2)
  })

  it('reste sur la dernière si toutes sont saisies', () => {
    const manches = [1, 2, 3, 4, 5].map((numero) => ({ numero, haut: [], bas: [] }))
    expect(prochaineMancheASaisir({ manches }, 5)).toBe(5)
  })
})

describe('mancheExistante', () => {
  it('retrouve une manche par numéro, ou null', () => {
    const d = duel({ manches: [{ numero: 2, haut: ['10'], bas: ['9'] }] })
    expect(mancheExistante(d, 2)?.haut).toEqual(['10'])
    expect(mancheExistante(d, 1)).toBeNull()
  })
})

describe('statutDuel', () => {
  it('bye', () => {
    expect(statutDuel(duel({ est_bye: true }))).toBe('bye')
  })
  it('adversaires inconnus', () => {
    expect(statutDuel(duel({ bas: null }))).toBe('attente_adversaires')
  })
  it('à saisir (aucun tir)', () => {
    expect(statutDuel(duel())).toBe('a_saisir')
  })
  it('en cours (des manches, pas encore tranché)', () => {
    const d = duel({
      manches: [{ numero: 1, haut: ['10'], bas: ['9'] }],
      resultat: {
        points_haut: 2,
        points_bas: 0,
        vainqueur: null,
        termine: false,
        barrage_requis: false,
      },
    })
    expect(statutDuel(d)).toBe('en_cours')
  })
  it('à valider (tranché, non validé)', () => {
    const d = duel({
      resultat: {
        points_haut: 6,
        points_bas: 0,
        vainqueur: 'haut',
        termine: true,
        barrage_requis: false,
      },
    })
    expect(statutDuel(d)).toBe('a_valider')
  })
  it('validé', () => {
    expect(statutDuel(duel({ validee_par: 'ROUX' }))).toBe('valide')
  })
})

describe('injecterManche (optimiste hors-ligne)', () => {
  const corps: SaisirManche = {
    tournoi_id: 1,
    phase_id: 2,
    match_numero: 1,
    numero: 1,
    valeurs_haut: ['10', '10', '10'],
    valeurs_bas: ['9', '9', '9'],
    identifiant_saisie: 'id-1',
  }

  it('ajoute la manche et marque le duel en attente', () => {
    const d = injecterManche(duel(), corps)
    expect(d.manches).toHaveLength(1)
    expect(d.manches[0]).toEqual({ numero: 1, haut: ['10', '10', '10'], bas: ['9', '9', '9'] })
    expect(d.en_attente).toBe(true)
  })

  it('remplace une manche de même numéro (réédition) et ne recompute pas le résultat', () => {
    const base = duel({
      manches: [{ numero: 1, haut: ['6', '6', '6'], bas: ['10', '10', '10'] }],
      resultat: {
        points_haut: 0,
        points_bas: 2,
        vainqueur: null,
        termine: false,
        barrage_requis: false,
      },
    })
    const d = injecterManche(base, corps)
    expect(d.manches).toHaveLength(1)
    expect(d.manches[0]?.haut).toEqual(['10', '10', '10'])
    expect(d.resultat?.points_bas).toBe(2) // résultat inchangé : autorité serveur (ADR-0049)
  })
})

describe('injecterBarrage (optimiste hors-ligne)', () => {
  it('pose le barrage et marque le duel en attente', () => {
    const corps: SaisirBarrage = {
      tournoi_id: 1,
      phase_id: 2,
      match_numero: 1,
      fleche_haut: '10',
      fleche_bas: '9',
      gagnant_designe: null,
      identifiant_saisie: 'id-b',
    }
    const d = injecterBarrage(duel(), corps)
    expect(d.barrage).toEqual({ haut: '10', bas: '9', gagnant_designe: null })
    expect(d.en_attente).toBe(true)
  })
})

describe('totalVolee', () => {
  it('somme les zones, M = 0', () => {
    expect(totalVolee(['10', '9', 'M'])).toBe(19)
    expect(totalVolee([])).toBe(0)
  })
})
