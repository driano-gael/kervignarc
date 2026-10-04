// Non-régression E00US024 : l'oracle est le comportement du formulaire avant l'extraction.

import { describe, expect, it } from 'vitest'

import { ARRETS_PAR_DEFAUT, type EtatArrets } from '../../shared/phases/arrets'
import { BAREME_DUEL_NON_REGLE } from '../../shared/phases/baremeDuel'
import { BIG_SHOOT_OFF_PAR_DEFAUT } from '../../shared/phases/bigShootOff'
import { COLLINE_PAR_DEFAUT } from '../../shared/phases/colline'
import { DECOUPAGE_PAR_DEFAUT } from '../../shared/phases/decoupage'
import { POULES_PAR_DEFAUT } from '../../shared/phases/poules'
import { PROFONDEUR_AU_PRESET } from '../../shared/phases/profondeur'
import { SUISSE_PAR_DEFAUT } from '../../shared/phases/suisse'
import type { Source } from '../patrimoine/api'
import {
  baremeSaisi,
  construireEtape,
  fichesOffertes,
  saisieInvalide,
  soumissionBloquee,
  type SaisieEtape,
} from './compositionEtape'

function saisie(surcharge: Partial<SaisieEtape> = {}): SaisieEtape {
  return {
    type: 'qualification',
    nbVolees: '20',
    nbFleches: '3',
    effectif: '',
    sources: [],
    profondeur: PROFONDEUR_AU_PRESET,
    poules: POULES_PAR_DEFAUT,
    bigShootOff: BIG_SHOOT_OFF_PAR_DEFAUT,
    suisse: SUISSE_PAR_DEFAUT,
    colline: COLLINE_PAR_DEFAUT,
    baremeDuel: BAREME_DUEL_NON_REGLE,
    equipes: null,
    decoupage: DECOUPAGE_PAR_DEFAUT,
    arrets: ARRETS_PAR_DEFAUT,
    titre: '',
    duree: '',
    ...surcharge,
  }
}

const ARRET_APRES_TOUR_1: EtatArrets = {
  lignes: [{ cle: 'a', apresTour: '1', portee: 'phase' }],
}

describe('fichesOffertes', () => {
  it('offre profondeur aux seuls tableaux', () => {
    expect(fichesOffertes('elimination_directe', DECOUPAGE_PAR_DEFAUT).enTableau).toBe(true)
    expect(fichesOffertes('placement', DECOUPAGE_PAR_DEFAUT).enTableau).toBe(true)
    expect(fichesOffertes('poules', DECOUPAGE_PAR_DEFAUT).enTableau).toBe(false)
  })

  it('réserve les équipes à l’élimination directe, pas à tout type à barème de duel', () => {
    const poules = fichesOffertes('poules', DECOUPAGE_PAR_DEFAUT)
    expect(poules.aBaremeDeDuel).toBe(true)
    expect(poules.estEliminationDirecte).toBe(false)
    expect(fichesOffertes('elimination_directe', DECOUPAGE_PAR_DEFAUT).estEliminationDirecte).toBe(
      true,
    )
    expect(fichesOffertes('placement', DECOUPAGE_PAR_DEFAUT).aBaremeDeDuel).toBe(false)
  })

  it('reconnaît chaque type à fiche propre', () => {
    expect(fichesOffertes('poules', DECOUPAGE_PAR_DEFAUT).estPoules).toBe(true)
    expect(fichesOffertes('big_shoot_off', DECOUPAGE_PAR_DEFAUT).estBigShootOff).toBe(true)
    expect(fichesOffertes('suisse', DECOUPAGE_PAR_DEFAUT).estSuisse).toBe(true)
    expect(fichesOffertes('colline', DECOUPAGE_PAR_DEFAUT).estColline).toBe(true)
    expect(fichesOffertes('qualification', DECOUPAGE_PAR_DEFAUT).estQualification).toBe(true)
    expect(fichesOffertes('barrage', DECOUPAGE_PAR_DEFAUT)).toEqual({
      enTableau: false,
      estPoules: false,
      estBigShootOff: false,
      estSuisse: false,
      estColline: false,
      aBaremeDeDuel: false,
      estEliminationDirecte: false,
      estQualification: false,
      arretable: false,
    })
  })

  it('rend arrêtable une qualification seulement si elle est découpée en plusieurs tours', () => {
    expect(fichesOffertes('qualification', { tours: '1' }).arretable).toBe(false)
    expect(fichesOffertes('qualification', { tours: '2' }).arretable).toBe(true)
    // Illisible ferme aussi la fiche.
    expect(fichesOffertes('qualification', { tours: '' }).arretable).toBe(false)
  })

  it('rend arrêtables les types qui annoncent leurs tours, quel que soit le découpage', () => {
    expect(fichesOffertes('elimination_directe', { tours: '1' }).arretable).toBe(true)
    expect(fichesOffertes('colline', { tours: '' }).arretable).toBe(true)
    expect(fichesOffertes('placement', { tours: '3' }).arretable).toBe(false)
    expect(fichesOffertes('echauffement', DECOUPAGE_PAR_DEFAUT).arretable).toBe(false)
  })
})

describe('baremeSaisi', () => {
  it('porte le barème d’une qualification aux deux valeurs lisibles', () => {
    expect(baremeSaisi(saisie())).toEqual({ nb_volees: 20, nb_fleches_par_volee: 3 })
  })

  it('rend null pour un brouillon de qualification sans barème complet', () => {
    expect(baremeSaisi(saisie({ nbVolees: '' }))).toBeNull()
    expect(baremeSaisi(saisie({ nbFleches: '' }))).toBeNull()
    expect(baremeSaisi(saisie({ nbVolees: 'vingt' }))).toBeNull()
    expect(baremeSaisi(saisie({ nbVolees: '0' }))).toBeNull()
  })

  it('rend null hors qualification, même aux valeurs lisibles', () => {
    expect(baremeSaisi(saisie({ type: 'elimination_directe' }))).toBeNull()
  })
})

describe('saisieInvalide', () => {
  it('accepte des champs vides ou entiers positifs', () => {
    expect(saisieInvalide(saisie())).toBe(false)
    expect(saisieInvalide(saisie({ nbVolees: '', nbFleches: '', effectif: '' }))).toBe(false)
    expect(saisieInvalide(saisie({ effectif: '1' }))).toBe(false)
  })

  it('refuse chacun des trois champs numériques illisible', () => {
    expect(saisieInvalide(saisie({ nbVolees: 'abc' }))).toBe(true)
    expect(saisieInvalide(saisie({ nbFleches: '2.5' }))).toBe(true)
    expect(saisieInvalide(saisie({ effectif: '0' }))).toBe(true)
  })
})

describe('soumissionBloquee', () => {
  it('laisse passer une saisie par défaut', () => {
    expect(soumissionBloquee(saisie())).toBe(false)
  })

  it('bloque une saisie numérique invalide', () => {
    expect(soumissionBloquee(saisie({ effectif: '-3' }))).toBe(true)
  })

  it('bloque un top N sans seuil sur un tableau, l’ignore ailleurs', () => {
    const topVide = { mode: 'top', seuil: '' } as const
    expect(soumissionBloquee(saisie({ type: 'elimination_directe', profondeur: topVide }))).toBe(
      true,
    )
    expect(soumissionBloquee(saisie({ type: 'poules', profondeur: topVide }))).toBe(false)
  })

  it('juge chaque fiche seulement sur son type', () => {
    const poules = { ...POULES_PAR_DEFAUT, taille: '' }
    expect(soumissionBloquee(saisie({ type: 'poules', poules }))).toBe(true)
    expect(soumissionBloquee(saisie({ type: 'suisse', poules }))).toBe(false)

    const bigShootOff = { ...BIG_SHOOT_OFF_PAR_DEFAUT, sortants: '' }
    expect(soumissionBloquee(saisie({ type: 'big_shoot_off', bigShootOff }))).toBe(true)
    expect(soumissionBloquee(saisie({ type: 'poules', bigShootOff }))).toBe(false)

    const suisse = { rondes: '' }
    expect(soumissionBloquee(saisie({ type: 'suisse', suisse }))).toBe(true)
    expect(soumissionBloquee(saisie({ type: 'colline', suisse }))).toBe(false)

    const colline = { manches: '', portee: '1' }
    expect(soumissionBloquee(saisie({ type: 'colline', colline }))).toBe(true)
    expect(soumissionBloquee(saisie({ type: 'suisse', colline }))).toBe(false)

    const decoupage = { tours: '' }
    expect(soumissionBloquee(saisie({ type: 'qualification', decoupage }))).toBe(true)
    expect(soumissionBloquee(saisie({ type: 'elimination_directe', decoupage }))).toBe(false)
  })

  it('bloque un barème de duel réglé mais illisible sur les types à duel', () => {
    const baremeDuel = {
      ...BAREME_DUEL_NON_REGLE,
      regle: true,
      par_defaut: { ...BAREME_DUEL_NON_REGLE.par_defaut, manches: '' },
    }
    expect(soumissionBloquee(saisie({ type: 'elimination_directe', baremeDuel }))).toBe(true)
    expect(soumissionBloquee(saisie({ type: 'placement', baremeDuel }))).toBe(false)
  })

  it('juge les arrêts quel que soit le type', () => {
    const arrets: EtatArrets = { lignes: [{ cle: 'a', apresTour: 'x', portee: 'phase' }] }
    expect(soumissionBloquee(saisie({ type: 'placement', arrets }))).toBe(true)
  })
})

describe('construireEtape', () => {
  it('porte l’ordre reçu, le barème et la validation fin de série d’une qualification', () => {
    const etape = construireEtape(saisie(), 4)
    expect(etape.ordre).toBe(4)
    expect(etape.type).toBe('qualification')
    expect(etape.bareme).toEqual({ nb_volees: 20, nb_fleches_par_volee: 3 })
    expect(etape.validation).toEqual({ type: 'fin_de_serie', n_volees: null })
  })

  it('ne porte ni barème ni validation pour une qualification en brouillon', () => {
    const etape = construireEtape(saisie({ nbVolees: '' }), 1)
    expect(etape.bareme).toBeNull()
    expect(etape.validation).toBeNull()
  })

  it('transmet sources et effectif lu, vide valant null', () => {
    const sources: Source[] = [
      { ordre_source: 1, nature: 'reste', rang_debut: 1, rang_fin: null, tour: null, issue: null },
    ]
    expect(construireEtape(saisie({ sources, effectif: '16' }), 2)).toMatchObject({
      sources,
      effectif: 16,
    })
    expect(construireEtape(saisie(), 1).effectif).toBeNull()
  })

  it('efface tout réglage étranger au type au lieu de l’envoyer', () => {
    const etape = construireEtape(
      saisie({
        type: 'barrage',
        profondeur: { mode: 'integral' },
        equipes: 'standard',
        decoupage: { tours: '2' },
        arrets: ARRET_APRES_TOUR_1,
      }),
      1,
    )
    expect(etape).toMatchObject({
      bareme: null,
      validation: null,
      profondeur: null,
      poules: null,
      big_shoot_off: null,
      suisse: null,
      colline: null,
      bareme_duel: null,
      equipes: null,
      decoupage: null,
      arrets: [],
    })
  })

  it('porte la profondeur d’un tableau, et null au preset', () => {
    expect(
      construireEtape(saisie({ type: 'placement', profondeur: { mode: 'integral' } }), 1)
        .profondeur,
    ).toEqual({ nom: 'un_vers_n', jusqu_au: null })
    expect(construireEtape(saisie({ type: 'elimination_directe' }), 1).profondeur).toBeNull()
  })

  it('porte le réglage propre à chaque type', () => {
    expect(construireEtape(saisie({ type: 'poules' }), 1).poules).not.toBeNull()
    expect(construireEtape(saisie({ type: 'big_shoot_off' }), 1).big_shoot_off).not.toBeNull()
    expect(construireEtape(saisie({ type: 'suisse' }), 1).suisse).toEqual({ nb_rondes: 5 })
    expect(construireEtape(saisie({ type: 'colline' }), 1).colline).toEqual({
      nb_manches: 5,
      portee_de_defi: 1,
    })
    expect(
      construireEtape(saisie({ type: 'elimination_directe', equipes: 'mixte' }), 1).equipes,
    ).toBe('mixte')
  })

  it('porte un barème de duel réglé, null non réglé', () => {
    const regle = { ...BAREME_DUEL_NON_REGLE, regle: true }
    expect(
      construireEtape(saisie({ type: 'suisse', baremeDuel: regle }), 1).bareme_duel,
    ).not.toBeNull()
    expect(construireEtape(saisie({ type: 'suisse' }), 1).bareme_duel).toBeNull()
  })

  it('porte découpage et arrêts d’une qualification découpée', () => {
    const etape = construireEtape(
      saisie({ decoupage: { tours: '2' }, arrets: ARRET_APRES_TOUR_1 }),
      1,
    )
    expect(etape.decoupage).toEqual({ nb_tours: 2 })
    expect(etape.arrets).toEqual([{ apres_tour: 1, portee: 'phase' }])
  })

  it('n’envoie aucun arrêt d’une qualification non découpée', () => {
    expect(construireEtape(saisie({ arrets: ARRET_APRES_TOUR_1 }), 1).arrets).toEqual([])
  })

  it('garde le titre sur tout type, vidé ou blanc valant retrait', () => {
    expect(construireEtape(saisie({ type: 'poules', titre: 'Tableau des jeunes' }), 1).titre).toBe(
      'Tableau des jeunes',
    )
    expect(construireEtape(saisie({ titre: '   ' }), 1).titre).toBeNull()
    expect(construireEtape(saisie({ titre: '' }), 1).titre).toBeNull()
  })

  it('convertit la durée prévue, vide valant null', () => {
    expect(construireEtape(saisie({ duree: '45' }), 1).duree_prevue).toBe(45)
    expect(construireEtape(saisie(), 1).duree_prevue).toBeNull()
  })
})
