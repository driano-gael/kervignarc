// Tests de la saisie d'un barrage (E06US003). Ils fixent les deux confusions qui feraient **perdre
// un archer à tort** : un groupe soumis à moitié, et un champ vide pris pour une absence.

import { describe, expect, it } from 'vitest'
import { mancheComplete, type SaisieTir, versTirs } from './barrage'

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
