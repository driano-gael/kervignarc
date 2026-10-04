// E00US024 — non-régression de ce que `PaveArcher`, `MessageErreurSaisie` et `NavigateurVolees`
// calculaient dans leur corps (règle 9).

import { describe, expect, it } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import type { Volee } from './api'
import { noterBrouillon } from './brouillons'
import { classesPastille, complementMeta, estRefusDePreseance, etatPave } from './pave'

function volee(numero: number, valeurs: string[], champs: Partial<Volee> = {}): Volee {
  return {
    numero,
    valeurs,
    saisie_par: 'DUPONT',
    validee_par: null,
    verrouillee: false,
    en_correction: false,
    correction_ouverte_par: null,
    lot_validation: null,
    saisie_le: null,
    ...champs,
  }
}

const BASE = {
  archerId: 12,
  volees: [volee(1, ['10', '9', '8'])],
  bareme: { nb_volees: 3, nb_fleches_par_volee: 3 },
  brouillons: {},
  ouverture: null,
  serieChargee: true,
  envoiEnCours: false,
}

describe('etatPave', () => {
  it('sans choix : la prochaine volée à saisir, tampon vide, zones actives', () => {
    expect(etatPave(BASE)).toEqual({
      numeroActif: 2,
      fleche: null,
      existante: null,
      verrouillee: false,
      buffer: [],
      frappable: true,
      zonesActives: true,
      effacable: false,
      enregistrable: false,
    })
  })

  it('volée choisie et pleine : enregistrable, zones bloquées tant que rien n’est visé', () => {
    const etat = etatPave({ ...BASE, ouverture: { numero: 1, fleche: null } })
    expect(etat.existante).toBe(BASE.volees[0])
    expect(etat.buffer).toEqual(['10', '9', '8'])
    expect(etat.zonesActives).toBe(false)
    expect(etat.effacable).toBe(true)
    expect(etat.enregistrable).toBe(true)
    expect(etat.frappable).toBe(true)
  })

  it('volée pleine avec une flèche visée : les zones se rouvrent pour la corriger', () => {
    const etat = etatPave({ ...BASE, ouverture: { numero: 1, fleche: 1 } })
    expect(etat.fleche).toBe(1)
    expect(etat.zonesActives).toBe(true)
  })

  it('le brouillon fait le tampon ; incomplet, il n’est pas enregistrable', () => {
    const brouillons = noterBrouillon({}, 12, 2, ['9', '9'])
    const etat = etatPave({ ...BASE, brouillons })
    expect(etat.buffer).toEqual(['9', '9'])
    expect(etat.effacable).toBe(true)
    expect(etat.enregistrable).toBe(false)
    expect(etat.zonesActives).toBe(true)
  })

  it('série pas chargée : ni frappe, ni zones, ni enregistrement — effacer reste permis', () => {
    const brouillons = noterBrouillon({}, 12, 1, ['9', '9', '9'])
    const etat = etatPave({ ...BASE, volees: [], brouillons, serieChargee: false })
    expect(etat.numeroActif).toBe(1)
    expect(etat.frappable).toBe(false)
    expect(etat.zonesActives).toBe(false)
    expect(etat.enregistrable).toBe(false)
    expect(etat.effacable).toBe(true)
  })

  it('volée verrouillée : tout est fermé', () => {
    const verrouillee = volee(1, ['10', '9', '8'], { verrouillee: true, validee_par: 'ROUX' })
    const etat = etatPave({
      ...BASE,
      volees: [verrouillee],
      ouverture: { numero: 1, fleche: 0 },
    })
    expect(etat.verrouillee).toBe(true)
    expect(etat.frappable).toBe(false)
    expect(etat.zonesActives).toBe(false)
    expect(etat.effacable).toBe(false)
    expect(etat.enregistrable).toBe(false)
  })

  it('envoi en cours : boutons fermés, mais la frappe n’est pas refusée par principe', () => {
    const etat = etatPave({ ...BASE, ouverture: { numero: 1, fleche: 0 }, envoiEnCours: true })
    expect(etat.zonesActives).toBe(false)
    expect(etat.effacable).toBe(false)
    expect(etat.enregistrable).toBe(false)
    expect(etat.frappable).toBe(true)
  })
})

describe('complementMeta', () => {
  it('rien à ajouter sur une volée nue', () => {
    expect(complementMeta(volee(1, ['10']))).toBe('')
  })

  it('validée : le validateur est nommé', () => {
    expect(complementMeta(volee(1, ['10'], { validee_par: 'ROUX' }))).toBe(' · validée par ROUX')
  })

  it('rendue en correction : le validateur est tu', () => {
    const rendue = volee(1, ['10'], { validee_par: 'ROUX', en_correction: true })
    expect(complementMeta(rendue)).toBe('')
  })

  it('en attente d’envoi hors ligne', () => {
    expect(complementMeta(volee(1, ['10'], { en_attente: true }))).toBe(' · en attente d’envoi')
  })

  it('horodatée : l’heure locale en tête, puis validation et attente', () => {
    const iso = '2026-10-04T08:42:00Z'
    const instant = new Date(iso)
    const heure = `${instant.getHours().toString().padStart(2, '0')}h${instant
      .getMinutes()
      .toString()
      .padStart(2, '0')}`
    const v = volee(1, ['10'], { saisie_le: iso, validee_par: 'ROUX', en_attente: true })
    expect(complementMeta(v)).toBe(` à ${heure} · validée par ROUX · en attente d’envoi`)
  })

  // DETTE-124 — défaut hérité, figé faute de pouvoir le corriger ici : attente à inverser au remède.
  it('horodatage illisible : « à » reste, sans heure (défaut connu)', () => {
    expect(complementMeta(volee(1, ['10'], { saisie_le: 'pas une date' }))).toBe(' à ')
  })
})

describe('estRefusDePreseance', () => {
  it('reconnaît le 409 de préséance', () => {
    const refus = new ErreurApi(409, 'ecriture_de_role_inferieur', 'Saisie par l’organisateur.')
    expect(estRefusDePreseance(refus)).toBe(true)
  })

  it('une autre erreur d’API n’en est pas un', () => {
    expect(estRefusDePreseance(new ErreurApi(409, 'archer_hors_cible', 'Non.'))).toBe(false)
  })

  it('le code seul ne suffit pas : il faut une erreur d’API', () => {
    const imitation = Object.assign(new Error('x'), { code: 'ecriture_de_role_inferieur' })
    expect(estRefusDePreseance(imitation)).toBe(false)
    expect(estRefusDePreseance(null)).toBe(false)
  })
})

describe('classesPastille', () => {
  it('volée non saisie, non visée : la classe de base seule', () => {
    expect(classesPastille(2, undefined, 1)).toBe('saisie__nav-volee')
  })

  it('saisie et visée', () => {
    expect(classesPastille(1, { verrouillee: false }, 1)).toBe(
      'saisie__nav-volee saisie__nav-volee--saisie saisie__nav-volee--actif',
    )
  })

  it('saisie et verrouillée, non visée', () => {
    expect(classesPastille(1, { verrouillee: true }, 2)).toBe(
      'saisie__nav-volee saisie__nav-volee--saisie saisie__nav-volee--verrou',
    )
  })
})
