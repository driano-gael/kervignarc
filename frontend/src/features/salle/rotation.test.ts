// Tests de la rotation d'un écran de salle (E07US004) — dérivés du CA « déroulé de vues […] avec
// cadence réglable » et « une prise de contrôle sait se terminer ».

import { describe, expect, it } from 'vitest'

import type { VueProgrammee } from '../ecrans/api'
import { formaterReste, resteDeLaPrise, vueCourante } from './rotation'

const DEROULE: VueProgrammee[] = [
  { vue: 'classement', cadence_s: 30 },
  { vue: 'plan_cibles', cadence_s: 20 },
  { vue: 'suivi_deroule', cadence_s: 10 },
]

describe('vueCourante', () => {
  it('ouvre sur la première vue', () => {
    expect(vueCourante(DEROULE, 0)).toEqual({
      index: 0,
      vue: DEROULE[0],
      reste_s: 30,
    })
  })

  it('bascule à la seconde vue une fois la cadence écoulée', () => {
    expect(vueCourante(DEROULE, 29)?.index).toBe(0)
    expect(vueCourante(DEROULE, 30)?.index).toBe(1)
    expect(vueCourante(DEROULE, 49)?.index).toBe(1)
    expect(vueCourante(DEROULE, 50)?.index).toBe(2)
  })

  it('boucle après un tour complet', () => {
    // 30 + 20 + 10 = 60 s : à 60 s on est revenu au point de départ, à 8 heures aussi.
    expect(vueCourante(DEROULE, 60)?.index).toBe(0)
    expect(vueCourante(DEROULE, 8 * 3600 + 35)?.index).toBe(1)
  })

  it('décompte le temps restant sur la vue courante', () => {
    expect(vueCourante(DEROULE, 35)?.reste_s).toBe(15)
  })

  it('distingue deux occurrences de la même vue par leur position', () => {
    // « classement, plan, classement » est un déroulé légitime : la vue qui intéresse le plus
    // revient plus souvent. C'est l'`index`, pas la vue, qui identifie l'étape.
    const repete: VueProgrammee[] = [
      { vue: 'classement', cadence_s: 10 },
      { vue: 'plan_cibles', cadence_s: 10 },
      { vue: 'classement', cadence_s: 10 },
    ]

    expect(vueCourante(repete, 0)?.index).toBe(0)
    expect(vueCourante(repete, 25)?.index).toBe(2)
  })

  it('encaisse une horloge qui recule', () => {
    // Une mise à l'heure NTP en cours de journée peut rendre un écart négatif. L'écran doit
    // continuer d'afficher **une** vue, pas s'éteindre.
    expect(vueCourante(DEROULE, -5)?.index).toBe(2)
  })

  it('rend null sur une séquence vide plutôt que de planter', () => {
    // Le serveur n'en produit jamais (`SequenceVuesVide`), mais un écran de salle qui casserait sur
    // une réponse inattendue serait la panne la plus coûteuse : personne n'est là pour le relancer.
    expect(vueCourante([], 12)).toBeNull()
  })
})

describe('resteDeLaPrise', () => {
  it('décompte localement à partir du reste annoncé par le serveur', () => {
    expect(resteDeLaPrise(600, 0)).toBe(600)
    expect(resteDeLaPrise(600, 120)).toBe(480)
  })

  it('ne descend jamais sous zéro', () => {
    expect(resteDeLaPrise(60, 90)).toBe(0)
  })

  it('rend null quand la prise n’a pas d’échéance', () => {
    expect(resteDeLaPrise(null, 999)).toBeNull()
  })
})

describe('formaterReste', () => {
  it('se lit de loin, sans zéros de tête ni deux-points', () => {
    expect(formaterReste(45)).toBe('45 s')
    expect(formaterReste(60)).toBe('1 min')
    expect(formaterReste(432)).toBe('7 min 12 s')
  })

  it('ne rend jamais de négatif', () => {
    expect(formaterReste(-3)).toBe('0 s')
  })
})
