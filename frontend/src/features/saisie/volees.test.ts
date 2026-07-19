import { describe, expect, it } from 'vitest'
import type { Grain, Volee } from './api'
import {
  heureSaisie,
  libelleGrain,
  nouvelIdentifiant,
  pointsZone,
  prochaineASaisir,
  quelSaisiePar,
  totalVolee,
  voleeExistante,
} from './volees'

function volee(numero: number, valeurs: string[], verrouillee = false): Volee {
  return {
    numero,
    valeurs,
    saisie_par: null,
    validee_par: verrouillee ? 'ROUX' : null,
    verrouillee,
    saisie_le: null,
  }
}

describe('pointsZone', () => {
  it('« M » (manqué) vaut 0 point', () => {
    expect(pointsZone('M')).toBe(0)
  })

  it('une zone numérique vaut sa valeur', () => {
    expect(pointsZone('10')).toBe(10)
    expect(pointsZone('7')).toBe(7)
  })

  it('une valeur inattendue vaut 0 (défensif)', () => {
    expect(pointsZone('X')).toBe(0)
  })
})

describe('totalVolee', () => {
  it('somme les points des flèches', () => {
    expect(totalVolee(['10', '9', 'M'])).toBe(19)
  })

  it('une volée vide vaut 0', () => {
    expect(totalVolee([])).toBe(0)
  })
})

describe('prochaineASaisir', () => {
  it('sans aucune volée, la première est à saisir', () => {
    expect(prochaineASaisir([], 20)).toBe(1)
  })

  it('avance dès qu’une volée est saisie, même non validée (le verrou est l’acte du scoreur)', () => {
    // 1 saisie mais pas verrouillée : le marqueur passe quand même à la 2.
    expect(prochaineASaisir([volee(1, ['9', '9', '9'])], 20)).toBe(2)
  })

  it('reprend le premier trou (une volée sautée reste à saisir)', () => {
    const volees = [volee(1, ['10', '9', '8']), volee(3, ['8', '8', '8'])]
    expect(prochaineASaisir(volees, 20)).toBe(2)
  })

  it('toutes les volées saisies → on reste sur la dernière (édition via le navigateur)', () => {
    const volees = [volee(1, ['10', '9', '8']), volee(2, ['9', '9', '9'])]
    expect(prochaineASaisir(volees, 2)).toBe(2)
  })
})

describe('voleeExistante', () => {
  it('retrouve une volée déjà saisie pour la rééditer', () => {
    const v = volee(3, ['8', '8', '8'])
    expect(voleeExistante([v], 3)).toEqual(v)
  })

  it('rend null si la volée n’a pas encore été saisie', () => {
    expect(voleeExistante([], 3)).toBeNull()
  })
})

describe('libelleGrain', () => {
  it('fin de série', () => {
    expect(libelleGrain({ grain: 'fin_de_serie', n_volees: null })).toBe(
      'Validation à la fin de la série',
    )
  })

  it('fin de duel', () => {
    expect(libelleGrain({ grain: 'fin_de_duel', n_volees: null })).toBe(
      'Validation à la fin du duel',
    )
  })

  it('toutes les N volées reprend le N', () => {
    const grain: Grain = { grain: 'toutes_les_n_volees', n_volees: 2 }
    expect(libelleGrain(grain)).toBe('Validation toutes les 2 volées')
  })

  it('grain absent → mention explicite', () => {
    expect(libelleGrain(null)).toBe('Grain de validation non défini')
  })
})

describe('heureSaisie', () => {
  it('formate l’heure locale en HHhMM', () => {
    // Entrée ISO **sans** offset → JS l'interprète en heure locale, donc `getHours()` est
    // déterministe quelle que soit la TZ du runner. En production, `saisie_le` est UTC (offset `Z`)
    // et s'affiche à l'heure murale de la salle ; ce test valide le **format**, pas la conversion TZ.
    expect(heureSaisie('2026-07-19T09:05:00')).toBe('09h05')
  })

  it('horodatage absent → chaîne vide', () => {
    expect(heureSaisie(null)).toBe('')
  })

  it('horodatage illisible → chaîne vide', () => {
    expect(heureSaisie('pas une date')).toBe('')
  })
})

describe('quelSaisiePar', () => {
  it('nouvelle volée → le marqueur actif signe', () => {
    expect(quelSaisiePar(null, 'DURAND')).toBe('DURAND')
  })

  it('ré-édition d’une volée existante → null (le domaine préserve le marqueur d’origine)', () => {
    const existante: Volee = {
      numero: 1,
      valeurs: ['10', '9', '8'],
      saisie_par: 'DURAND',
      validee_par: null,
      verrouillee: false,
      saisie_le: null,
    }
    expect(quelSaisiePar(existante, 'MARTIN')).toBeNull()
  })
})

describe('nouvelIdentifiant', () => {
  it('produit un UUID quand crypto.randomUUID est disponible (contexte sécurisé)', () => {
    expect(nouvelIdentifiant()).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    )
  })

  it('retombe sur getRandomValues quand randomUUID est absent (LAN http, hors contexte sécurisé)', () => {
    const original = globalThis.crypto.randomUUID
    // Simule un contexte non sécurisé : `randomUUID` y est absent de l'objet `crypto`.
    // @ts-expect-error — on retire volontairement la méthode pour exercer le repli.
    globalThis.crypto.randomUUID = undefined
    try {
      const id = nouvelIdentifiant()
      // UUID v4 : 13ᵉ nibble = 4, 17ᵉ ∈ {8,9,a,b}.
      expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i)
      expect(id).not.toBe(nouvelIdentifiant())
    } finally {
      globalThis.crypto.randomUUID = original
    }
  })
})
