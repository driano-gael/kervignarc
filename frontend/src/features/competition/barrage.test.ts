// Tests de la saisie d'un barrage (E06US003). Ils fixent les deux confusions qui feraient **perdre
// un archer à tort** : un groupe soumis à moitié, et un champ vide pris pour une absence.

import { describe, expect, it } from 'vitest'
import {
  correspond,
  depuisTirs,
  mancheComplete,
  memesTireurs,
  type SaisieTir,
  versTirs,
} from './barrage'

const NOTE = (score: string): SaisieTir => ({ score, distance: '', absent: false })
const ABSENT: SaisieTir = { score: '', distance: '', absent: true }
const VIDE: SaisieTir = { score: '', distance: '', absent: false }

describe('mancheComplete', () => {
  it('refuse un groupe dont un tireur n’est ni noté ni déclaré absent', () => {
    expect(mancheComplete([1, 2], { 1: NOTE('9'), 2: VIDE })).toBe(false)
  })

  it('refuse un groupe dont un tireur n’a aucune saisie du tout', () => {
    expect(mancheComplete([1, 2], { 1: NOTE('9') })).toBe(false)
  })

  it('accepte un groupe entièrement noté', () => {
    expect(mancheComplete([1, 2], { 1: NOTE('9'), 2: NOTE('10') })).toBe(true)
  })

  it('accepte un absent — c’est une issue réglementaire, pas une saisie manquante', () => {
    expect(mancheComplete([1, 2], { 1: NOTE('9'), 2: ABSENT })).toBe(true)
  })

  it('accepte un zéro, qui est un vrai score et non un champ vide', () => {
    expect(mancheComplete([1], { 1: NOTE('0') })).toBe(true)
  })
})

describe('versTirs', () => {
  it('n’envoie un score nul que pour un absent coché', () => {
    const tirs = versTirs([1, 2], { 1: NOTE('9'), 2: ABSENT })
    expect(tirs).toEqual([
      { archer_id: 1, score: 9, distance_au_centre: null },
      { archer_id: 2, score: null, distance_au_centre: null },
    ])
  })

  it('laisse la distance nulle quand elle n’a pas été mesurée', () => {
    // Cas le plus fréquent du jour J : le juge mesure la flèche litigieuse, rarement les deux. Une
    // mesure absente est une **inconnue** — la replier sur 0 ferait gagner le tir non mesuré.
    expect(versTirs([1], { 1: NOTE('10') })).toEqual([
      { archer_id: 1, score: 10, distance_au_centre: null },
    ])
  })

  it('transmet la distance mesurée', () => {
    const tirs = versTirs([1], { 1: { score: '10', distance: '17', absent: false } })
    expect(tirs).toEqual([{ archer_id: 1, score: 10, distance_au_centre: 17 }])
  })

  it('ignore le score saisi si l’archer est finalement déclaré absent', () => {
    const tirs = versTirs([1], { 1: { score: '9', distance: '', absent: true } })
    expect(tirs).toEqual([{ archer_id: 1, score: null, distance_au_centre: null }])
  })
})

describe('depuisTirs', () => {
  it('recoche « absent » sur un score nul, plutôt que de laisser un champ vide', () => {
    // Le contresens (« pas encore noté ») changerait le sens de la correction, et laisserait le
    // bouton grisé.
    expect(depuisTirs([{ archer_id: 1, score: null, distance_au_centre: null }])).toEqual({
      1: { score: '', distance: '', absent: true },
    })
  })

  it('restitue score et distance tels qu’ils ont été enregistrés', () => {
    expect(depuisTirs([{ archer_id: 2, score: 9, distance_au_centre: 17 }])).toEqual({
      2: { score: '9', distance: '17', absent: false },
    })
  })

  it('distingue un zéro d’une absence', () => {
    expect(depuisTirs([{ archer_id: 3, score: 0, distance_au_centre: null }])).toEqual({
      3: { score: '0', distance: '', absent: false },
    })
  })

  it('rend un formulaire vierge sans tir', () => {
    expect(depuisTirs(undefined)).toEqual({})
  })
})

describe('memesTireurs', () => {
  it('ignore l’ordre', () => {
    expect(memesTireurs([1, 2], [2, 1])).toBe(true)
  })

  it('distingue un groupe élargi — le cas du barrage périmé', () => {
    expect(memesTireurs([1, 2], [1, 2, 3])).toBe(false)
  })

  it('distingue un groupe réduit', () => {
    expect(memesTireurs([1, 2, 3], [1, 2])).toBe(false)
  })
})

describe('correspond', () => {
  it('replie les accents — « Créac’h » répond à « creach »', () => {
    expect(correspond("Créac'h", 'Yann', "creac'h")).toBe(true)
  })

  it('replie la casse', () => {
    expect(correspond('MARTIN', 'Alice', 'martin')).toBe(true)
  })

  it('cherche aussi dans le prénom', () => {
    expect(correspond('MARTIN', 'Alice', 'alice')).toBe(true)
  })

  it('rend tout le monde sur une recherche vide', () => {
    expect(correspond('MARTIN', 'Alice', '   ')).toBe(true)
  })

  it('exclut ce qui ne correspond pas', () => {
    expect(correspond('MARTIN', 'Alice', 'durand')).toBe(false)
  })
})
