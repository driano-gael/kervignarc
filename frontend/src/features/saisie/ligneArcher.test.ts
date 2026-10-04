// E00US024 — non-régression de ce que `LigneArcher` calculait dans son corps (règle 9).

import { describe, expect, it } from 'vitest'
import type { Bareme, Volee } from './api'
import { noterBrouillon } from './brouillons'
import { etatLigne, libelleCase, totalAffiche } from './ligneArcher'

const TABLE = { '10': 10, '9': 9, '8': 8, M: 0 }
const BAREME: Bareme = {
  nb_volees: 3,
  nb_fleches_par_volee: 3,
  nb_fleches_total: 9,
  score_max: 30,
  points_par_zone: TABLE,
}

function volee(numero: number, valeurs: string[], verrouillee = false): Volee {
  return {
    numero,
    valeurs,
    saisie_par: null,
    validee_par: verrouillee ? 'ROUX' : null,
    verrouillee,
    en_correction: false,
    correction_ouverte_par: null,
    lot_validation: null,
    saisie_le: null,
  }
}

const BASE = {
  archerId: 12,
  volees: [volee(1, ['10', '9', '8'], true), volee(2, ['M', '10', '9'])],
  serieLue: true,
  bareme: BAREME,
  brouillons: {},
  ouverture: null,
  actif: false,
}

describe('totalAffiche', () => {
  it('somme la volée selon la table', () => {
    expect(totalAffiche(['10', '9', 'M'], TABLE)).toBe(19)
  })

  it('barème non lu : « ? », jamais 0', () => {
    expect(totalAffiche(['10'], null)).toBe('?')
  })
})

describe('etatLigne', () => {
  it('série lue : avancement, cumul saisi et prochaine volée à saisir', () => {
    expect(etatLigne(BASE)).toEqual({
      nbSaisies: 2,
      cumul: 46,
      numero: 3,
      enCours: [],
      caseActivable: true,
      caseEnCours: null,
    })
  })

  it('série pas encore lue : avancement et cumul en « ? »', () => {
    const etat = etatLigne({ ...BASE, volees: [], serieLue: false })
    expect(etat.nbSaisies).toBe('?')
    expect(etat.cumul).toBe('?')
    expect(etat.caseActivable).toBe(false)
  })

  it('barème non lu : cumul « ? » et pas de volée ouverte', () => {
    const etat = etatLigne({ ...BASE, bareme: null })
    expect(etat.cumul).toBe('?')
    expect(etat.numero).toBeNull()
    expect(etat.enCours).toEqual([])
    expect(etat.caseActivable).toBe(true)
    // L'avancement, lui, ne dépend que de la série.
    expect(etat.nbSaisies).toBe(2)
  })

  it('la volée ouverte suit le choix de l’archer actif, et se pré-remplit du persisté', () => {
    const etat = etatLigne({ ...BASE, ouverture: { numero: 2, fleche: null }, actif: true })
    expect(etat.numero).toBe(2)
    expect(etat.enCours).toEqual(['M', '10', '9'])
    expect(etat.caseEnCours).toBe(3)
  })

  it('le brouillon passe devant le persisté sur la volée ouverte', () => {
    const brouillons = noterBrouillon({}, 12, 3, ['9'])
    const etat = etatLigne({ ...BASE, brouillons, actif: true })
    expect(etat.enCours).toEqual(['9'])
    expect(etat.caseEnCours).toBe(1)
  })

  it('la case marquée est la flèche visée quand il y en a une', () => {
    const etat = etatLigne({ ...BASE, ouverture: { numero: 2, fleche: 0 }, actif: true })
    expect(etat.caseEnCours).toBe(0)
  })

  it('pas de case marquée hors archer actif', () => {
    const etat = etatLigne({ ...BASE, ouverture: { numero: 2, fleche: 0 }, actif: false })
    expect(etat.caseEnCours).toBeNull()
  })

  it('une volée verrouillée ouverte rend ses cases inactivables', () => {
    const etat = etatLigne({ ...BASE, ouverture: { numero: 1, fleche: null } })
    expect(etat.caseActivable).toBe(false)
  })
})

describe('libelleCase', () => {
  it('nomme la flèche, l’archer et sa valeur', () => {
    expect(libelleCase(0, 'DUPONT', '10')).toBe('Flèche 1 de DUPONT : 10')
  })

  it('case vide : sans valeur', () => {
    expect(libelleCase(2, 'DUPONT', undefined)).toBe('Flèche 3 de DUPONT')
  })
})
