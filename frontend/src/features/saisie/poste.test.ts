// E00US024 — non-régression des décisions sorties de `Saisie` : l'oracle est le comportement
// d'avant l'extraction (règle 9), cas limites compris.

import { describe, expect, it } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import type { LigneGrille, Volee } from './api'
import {
  affichagePoste,
  archerActifParmi,
  cibleClose,
  marqueurActifParmi,
  ouvertureDeLArcher,
  signatureComposition,
} from './poste'

function ligne(archer_id: number, nom: string, forfait = false): LigneGrille {
  return { position: 'A', archer_id, nom, prenom: 'P', zones: ['10'], forfait }
}

function volee(numero: number, verrouillee: boolean): Volee {
  return {
    numero,
    valeurs: ['10'],
    saisie_par: null,
    validee_par: verrouillee ? 'ROUX' : null,
    verrouillee,
    en_correction: false,
    correction_ouverte_par: null,
    lot_validation: null,
    saisie_le: null,
  }
}

const LIGNES = [ligne(12, 'DUPONT'), ligne(34, 'MARTIN')]
const departNonDefini = new ErreurApi(409, 'depart_courant_non_defini', 'Départ ?')

describe('affichagePoste', () => {
  it('chargement : rien que le titre', () => {
    expect(affichagePoste({ enErreur: false, erreur: null, succes: false, nbLignes: 0 })).toEqual({
      besoinDepart: false,
      confirmation: false,
      selecteurDepart: false,
      messageErreur: false,
      grilleVide: false,
      travail: false,
    })
  })

  it('départ non fixé : un état attendu, pas une erreur — sélecteur obligatoire et confirmation', () => {
    expect(
      affichagePoste({ enErreur: true, erreur: departNonDefini, succes: false, nbLignes: 0 }),
    ).toEqual({
      besoinDepart: true,
      confirmation: true,
      selecteurDepart: true,
      messageErreur: false,
      grilleVide: false,
      travail: false,
    })
  })

  it('une autre erreur d’API est une erreur dure : message, ni sélecteur ni confirmation', () => {
    const autre = new ErreurApi(500, 'erreur_interne', 'Boum')
    expect(affichagePoste({ enErreur: true, erreur: autre, succes: false, nbLignes: 0 })).toEqual({
      besoinDepart: false,
      confirmation: false,
      selecteurDepart: false,
      messageErreur: true,
      grilleVide: false,
      travail: false,
    })
  })

  it('le code seul ne suffit pas : une erreur réseau n’est pas un départ manquant', () => {
    const reseau = Object.assign(new Error('réseau'), { code: 'depart_courant_non_defini' })
    const affichage = affichagePoste({ enErreur: true, erreur: reseau, succes: false, nbLignes: 0 })
    expect(affichage.besoinDepart).toBe(false)
    expect(affichage.messageErreur).toBe(true)
  })

  it('une erreur reportée hors état d’erreur ne compte pas', () => {
    const affichage = affichagePoste({
      enErreur: false,
      erreur: departNonDefini,
      succes: false,
      nbLignes: 0,
    })
    expect(affichage.besoinDepart).toBe(false)
    expect(affichage.selecteurDepart).toBe(false)
  })

  it('grille vide servie : confirmation, sélecteur repliable et message « aucun archer »', () => {
    expect(affichagePoste({ enErreur: false, erreur: null, succes: true, nbLignes: 0 })).toEqual({
      besoinDepart: false,
      confirmation: true,
      selecteurDepart: true,
      messageErreur: false,
      grilleVide: true,
      travail: false,
    })
  })

  it('grille peuplée : zone de travail, pas de confirmation', () => {
    expect(affichagePoste({ enErreur: false, erreur: null, succes: true, nbLignes: 4 })).toEqual({
      besoinDepart: false,
      confirmation: false,
      selecteurDepart: true,
      messageErreur: false,
      grilleVide: false,
      travail: true,
    })
  })
})

describe('archerActifParmi', () => {
  it('garde le choix tant que l’archer est dans la grille', () => {
    expect(archerActifParmi(LIGNES, 34)).toBe(34)
  })

  it('aucun choix : aucun archer actif — le pavé n’est pas ouvert d’office', () => {
    expect(archerActifParmi(LIGNES, null)).toBeNull()
  })

  it('choix devenu obsolète (archer sorti de la grille) : pas de repli sur un autre archer', () => {
    expect(archerActifParmi(LIGNES, 99)).toBeNull()
  })
})

describe('marqueurActifParmi', () => {
  it('garde le marqueur choisi s’il est dans la grille', () => {
    expect(marqueurActifParmi(LIGNES, 'MARTIN')).toBe('MARTIN')
  })

  it('sans choix, se replie sur le premier archer — une volée part toujours signée', () => {
    expect(marqueurActifParmi(LIGNES, null)).toBe('DUPONT')
  })

  it('choix obsolète : repli sur le premier archer', () => {
    expect(marqueurActifParmi(LIGNES, 'DURAND')).toBe('DUPONT')
  })

  it('grille vide : pas de marqueur', () => {
    expect(marqueurActifParmi([], 'DUPONT')).toBeNull()
  })
})

describe('ouvertureDeLArcher', () => {
  const ouverture = { archerId: 12, numero: 3, fleche: 1 }

  it('l’ouverture de l’archer actif reste', () => {
    expect(ouvertureDeLArcher(ouverture, 12)).toBe(ouverture)
  })

  it('retombe dès que l’archer actif change', () => {
    expect(ouvertureDeLArcher(ouverture, 34)).toBeNull()
  })

  it('retombe quand plus aucun archer n’est actif', () => {
    expect(ouvertureDeLArcher(ouverture, null)).toBeNull()
  })

  it('rien d’ouvert : rien', () => {
    expect(ouvertureDeLArcher(null, 12)).toBeNull()
  })
})

describe('cibleClose', () => {
  const complete = [volee(1, true), volee(2, true)]

  it('toutes les séries complètes et verrouillées : close', () => {
    expect(cibleClose(LIGNES, [complete, complete], 2)).toBe(true)
  })

  it('une volée saisie mais pas verrouillée suffit à garder la cible ouverte', () => {
    expect(cibleClose(LIGNES, [complete, [volee(1, true), volee(2, false)]], 2)).toBe(false)
  })

  it('une série incomplète garde la cible ouverte', () => {
    expect(cibleClose(LIGNES, [complete, [volee(1, true)]], 2)).toBe(false)
  })

  it('un archer forfait ne bloque pas la cible, même sans série', () => {
    const lignes = [ligne(12, 'DUPONT'), ligne(34, 'MARTIN', true)]
    expect(cibleClose(lignes, [complete, undefined], 2)).toBe(true)
  })

  it('une série non lue n’est pas close', () => {
    expect(cibleClose(LIGNES, [complete, undefined], 2)).toBe(false)
  })

  it('barème inconnu : jamais close', () => {
    expect(cibleClose(LIGNES, [complete, complete], null)).toBe(false)
  })

  it('grille vide : jamais close', () => {
    expect(cibleClose([], [], 2)).toBe(false)
  })
})

describe('signatureComposition', () => {
  it('indifférente à l’ordre', () => {
    expect(signatureComposition([34, 12, 7])).toBe(signatureComposition([7, 34, 12]))
  })

  it('tri numérique, pas lexicographique', () => {
    expect(signatureComposition([10, 9])).toBe('9,10')
  })

  it('change avec la composition', () => {
    expect(signatureComposition([12, 34])).not.toBe(signatureComposition([12, 35]))
  })

  it('ne trie pas en place le tableau reçu', () => {
    const ids = [34, 12]
    signatureComposition(ids)
    expect(ids).toEqual([34, 12])
  })

  it('grille vide : chaîne vide', () => {
    expect(signatureComposition([])).toBe('')
  })
})
