// Le barème des duels côté écran (E01US011) — dérivé des CA de `stories/E01-configuration.md`.

import { describe, expect, it } from 'vitest'

import {
  BAREME_DUEL_NON_REGLE,
  armesDistinctes,
  ecartsDArmes,
  depuisReglage,
  estPoulies,
  estValide,
  presetClub,
  presetFfta,
  presetFftaEquipe,
  presetFftaMixte,
  versReglage,
  type EtatBaremeDuel,
  type ReglageBaremeDuel,
} from './baremeDuel'

const CLUB_AVEC_POULIES: ReglageBaremeDuel = {
  par_defaut: {
    mode: 'sets',
    nb_manches: 5,
    nb_fleches_par_volee: 3,
    points_pour_gagner: 4,
    nb_fleches_barrage: 1,
  },
  surcharges: [
    {
      arme: 'Arc à poulies',
      bareme: {
        mode: 'cumul',
        nb_manches: 5,
        nb_fleches_par_volee: 3,
        points_pour_gagner: 0,
        nb_fleches_barrage: 1,
      },
    },
  ],
}

describe('versReglage / depuisReglage', () => {
  it('une phase non réglée envoie null (CA 3 : le serveur garde son défaut)', () => {
    expect(versReglage(BAREME_DUEL_NON_REGLE)).toBeNull()
    expect(depuisReglage(null).regle).toBe(false)
  })

  it('fait l’aller-retour d’un réglage complet', () => {
    expect(versReglage(depuisReglage(CLUB_AVEC_POULIES))).toEqual(CLUB_AVEC_POULIES)
  })

  it('refuse un seuil de sets inatteignable', () => {
    const etat = depuisReglage(CLUB_AVEC_POULIES)
    const faux: EtatBaremeDuel = { ...etat, par_defaut: { ...etat.par_defaut, points: '11' } }
    expect(estValide(faux)).toBe(false)
  })

  it('ignore le seuil au cumul et envoie 0', () => {
    const etat = depuisReglage(CLUB_AVEC_POULIES)
    const cumul: EtatBaremeDuel = {
      ...etat,
      par_defaut: { ...etat.par_defaut, mode: 'cumul', points: '' },
    }
    expect(versReglage(cumul)?.par_defaut.points_pour_gagner).toBe(0)
  })

  it('refuse deux surcharges pour la même arme, sans tenir compte de la casse (CA 1)', () => {
    const etat = depuisReglage(CLUB_AVEC_POULIES)
    const doublon: EtatBaremeDuel = {
      ...etat,
      surcharges: [...etat.surcharges, { ...etat.surcharges[0]!, arme: ' ARC À POULIES ' }],
    }
    expect(estValide(doublon)).toBe(false)
  })

  it.each(['0', '', '13', '1.5'])('refuse %j flèche(s) de barrage (E13US003 CA 2)', (barrage) => {
    const etat = depuisReglage(CLUB_AVEC_POULIES)
    const faux: EtatBaremeDuel = { ...etat, par_defaut: { ...etat.par_defaut, barrage } }
    expect(estValide(faux)).toBe(false)
  })

  it('refuse une surcharge sans arme', () => {
    const etat = depuisReglage(CLUB_AVEC_POULIES)
    const vide: EtatBaremeDuel = { ...etat, surcharges: [{ ...etat.surcharges[0]!, arme: '  ' }] }
    expect(estValide(vide)).toBe(false)
  })
})

describe('presets (CA 2)', () => {
  const armes = ['Arc classique', 'Arc à poulies', 'arc à poulies', 'Arc nu']

  it('FFTA : sets à 6, poulies au cumul, une seule surcharge par arme distincte', () => {
    const reglage = versReglage(presetFfta(armes))
    expect(reglage?.par_defaut.points_pour_gagner).toBe(6)
    expect(reglage?.surcharges).toEqual([
      expect.objectContaining({
        arme: 'Arc à poulies',
        bareme: expect.objectContaining({ mode: 'cumul' }),
      }),
    ])
  })

  it('club : sets à 4, et les poulies restent au cumul', () => {
    const reglage = versReglage(presetClub(armes))
    expect(reglage?.par_defaut.points_pour_gagner).toBe(4)
    expect(reglage?.surcharges.map((s) => s.bareme.mode)).toEqual(['cumul'])
  })

  it('sans arme connue, un preset ne pose aucune surcharge', () => {
    expect(versReglage(presetFfta([]))?.surcharges).toEqual([])
  })
})

describe('presets FFTA équipe (E13US003 CA 4)', () => {
  const armes = ['Arc classique', 'Arc à poulies']

  it('équipe : 4 manches de 6 flèches, premier à 5, barrage à 3 — poulies au cumul', () => {
    expect(versReglage(presetFftaEquipe(armes))).toEqual({
      par_defaut: {
        mode: 'sets',
        nb_manches: 4,
        nb_fleches_par_volee: 6,
        points_pour_gagner: 5,
        nb_fleches_barrage: 3,
      },
      surcharges: [
        {
          arme: 'Arc à poulies',
          bareme: {
            mode: 'cumul',
            nb_manches: 4,
            nb_fleches_par_volee: 6,
            points_pour_gagner: 0,
            nb_fleches_barrage: 3,
          },
        },
      ],
    })
  })

  it('mixte : 4 manches de 4 flèches, premier à 5, barrage à 2 — poulies au cumul', () => {
    expect(versReglage(presetFftaMixte(armes))).toEqual({
      par_defaut: {
        mode: 'sets',
        nb_manches: 4,
        nb_fleches_par_volee: 4,
        points_pour_gagner: 5,
        nb_fleches_barrage: 2,
      },
      surcharges: [
        {
          arme: 'Arc à poulies',
          bareme: {
            mode: 'cumul',
            nb_manches: 4,
            nb_fleches_par_volee: 4,
            points_pour_gagner: 0,
            nb_fleches_barrage: 2,
          },
        },
      ],
    })
  })

  it('les presets individuels gardent un barrage à une flèche', () => {
    expect(versReglage(presetFfta(armes))?.par_defaut.nb_fleches_barrage).toBe(1)
    expect(versReglage(presetClub(armes))?.surcharges[0]?.bareme.nb_fleches_barrage).toBe(1)
  })
})

describe('armes', () => {
  it('reconnaît les poulies comme le serveur', () => {
    expect(estPoulies('Arc à Poulies')).toBe(true)
    expect(estPoulies('Compound')).toBe(true)
    expect(estPoulies('Arc classique')).toBe(false)
  })

  it('déduplique et trie les armes des catégories', () => {
    expect(armesDistinctes(['Arc nu', null, ' arc nu', 'Arc classique', ''])).toEqual([
      'Arc classique',
      'Arc nu',
    ])
  })
})

describe('écarts entre le réglage et les armes connues (ADR-0117)', () => {
  it('signale un arc à poulies que nulle surcharge ne couvre', () => {
    const etat = presetFfta(['Arc classique'])
    expect(ecartsDArmes(etat, ['Arc classique', 'Compound']).poulieSansSurcharge).toEqual([
      'Compound',
    ])
  })

  it('signale une surcharge dont aucune catégorie ne porte l’arme', () => {
    const etat = presetFfta(['Arc à poulies'])
    expect(ecartsDArmes(etat, ['Arc classique']).surchargeOrpheline).toEqual(['Arc à poulies'])
  })

  it('ne signale rien quand le preset a été posé sur les armes du tournoi', () => {
    const armes = ['Arc classique', 'Arc à poulies']
    expect(ecartsDArmes(presetClub(armes), armes)).toEqual({
      poulieSansSurcharge: [],
      surchargeOrpheline: [],
    })
  })

  it('ne signale rien sur une phase non réglée : le défaut reconnaît les poulies au nom', () => {
    expect(ecartsDArmes(BAREME_DUEL_NON_REGLE, ['Compound']).poulieSansSurcharge).toEqual([])
  })
})

describe('un défaut au cumul couvre déjà les poulies', () => {
  it('ne signale aucun arc à poulies sans surcharge', () => {
    const etat = presetFfta([])
    const auCumul = { ...etat, par_defaut: { ...etat.par_defaut, mode: 'cumul' as const } }
    expect(ecartsDArmes(auCumul, ['Compound']).poulieSansSurcharge).toEqual([])
  })
})
