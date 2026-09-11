// Tests de la logique pure du panneau de validation (E16US019).
//
// Dérivés du CA « l'écran dit ce qu'il fait » : la confirmation doit **nommer** les volées qu'une
// annulation rouvre, et l'écran doit distinguer « comptée » de « saisissable ».

import { describe, expect, it } from 'vitest'
import type { Serie, Volee } from '../saisie/api'
import {
  aValider,
  avertissementAnnulation,
  estValidee,
  etatVolee,
  voleesQueLAnnulationRouvre,
  voleesQueValiderReferme,
} from './etat'

function volee(numero: number, options: Partial<Volee> = {}): Volee {
  return {
    numero,
    valeurs: ['10', '9', '8'],
    saisie_par: 'DURAND',
    validee_par: null,
    verrouillee: false,
    en_correction: false,
    correction_ouverte_par: null,
    lot_validation: null,
    saisie_le: null,
    ...options,
  }
}

function serie(volees: Volee[]): Serie {
  return { tournoi_id: 1, archer_id: 7, cumul: 0, volees }
}

const VALIDEE = { validee_par: 'MARTIN', verrouillee: true, lot_validation: 1 }

describe('voleesQueLAnnulationRouvre', () => {
  it('nomme tout le lot, pas la seule volée cliquée', () => {
    const feuille = serie([volee(1, VALIDEE), volee(2, VALIDEE)])

    expect(voleesQueLAnnulationRouvre(feuille, 1)).toEqual([1, 2])
  })

  it('ne nomme pas les volées d’un autre lot', () => {
    const feuille = serie([
      volee(1, VALIDEE),
      volee(2, { validee_par: 'MARTIN', verrouillee: true, lot_validation: 2 }),
    ])

    expect(voleesQueLAnnulationRouvre(feuille, 1)).toEqual([1])
  })

  it('ne nomme rien sur une volée jamais validée', () => {
    expect(voleesQueLAnnulationRouvre(serie([volee(1)]), 1)).toEqual([])
  })

  it('ne nomme rien sur une volée déjà en correction', () => {
    const feuille = serie([volee(1, { ...VALIDEE, verrouillee: false, en_correction: true })])

    expect(voleesQueLAnnulationRouvre(feuille, 1)).toEqual([])
  })
})

describe('avertissementAnnulation', () => {
  it('énumère les volées rouvertes et dit que le score reste au classement', () => {
    const feuille = serie([volee(1, VALIDEE), volee(2, VALIDEE)])

    const texte = avertissementAnnulation(feuille, 1)

    expect(texte).toContain('Les volées 1, 2')
    expect(texte).toContain('classement')
  })

  it('accorde au singulier pour un lot d’une volée', () => {
    expect(avertissementAnnulation(serie([volee(1, VALIDEE)]), 1)).toContain(
      'La volée 1 redevient saisissable',
    )
  })
})

describe('état d’une volée', () => {
  it('une volée en correction reste comptée', () => {
    const enCorrection = volee(1, { ...VALIDEE, verrouillee: false, en_correction: true })

    expect(estValidee(enCorrection)).toBe(true)
    expect(etatVolee(enCorrection)).toBe('en_correction')
  })

  it('distingue validée, en correction et en cours', () => {
    expect(etatVolee(volee(1, VALIDEE))).toBe('validee')
    expect(etatVolee(volee(2))).toBe('en_cours')
  })
})

describe('aValider', () => {
  it('est vrai tant qu’une volée n’est pas verrouillée', () => {
    expect(aValider(serie([volee(1, VALIDEE), volee(2)]))).toBe(true)
  })

  it('est vrai après une annulation — la correction est à refermer', () => {
    const feuille = serie([volee(1, { ...VALIDEE, verrouillee: false, en_correction: true })])

    expect(aValider(feuille)).toBe(true)
  })

  it('est faux sur une feuille entièrement validée', () => {
    expect(aValider(serie([volee(1, VALIDEE), volee(2, VALIDEE)]))).toBe(false)
  })
})

describe('voleesQueValiderReferme', () => {
  it('nomme le lot que « Valider » refermerait', () => {
    const feuille = serie([
      volee(1, { ...VALIDEE, verrouillee: false, en_correction: true }),
      volee(2, { ...VALIDEE, verrouillee: false, en_correction: true }),
    ])

    expect(voleesQueValiderReferme(feuille)).toEqual([1, 2])
  })

  it('ne nomme que le lot le plus ancien — le serveur en referme un par geste', () => {
    const feuille = serie([
      volee(1, { ...VALIDEE, verrouillee: false, en_correction: true }),
      volee(2, {
        validee_par: 'MARTIN',
        lot_validation: 2,
        verrouillee: false,
        en_correction: true,
      }),
    ])

    expect(voleesQueValiderReferme(feuille)).toEqual([1])
  })

  it('est vide quand le bouton validera une saisie neuve', () => {
    expect(voleesQueValiderReferme(serie([volee(1, VALIDEE), volee(2)]))).toEqual([])
  })
})
