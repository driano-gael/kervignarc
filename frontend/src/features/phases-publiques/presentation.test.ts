// Tests des règles de lecture de l'index des phases publiques (E05US031).
//
// Ces deux fonctions décident **ce qui s'affiche sur l'écran projeté du gymnase**, où personne ne
// peut corriger un mauvais choix : une phase mal élue y reste huit heures. C'est exactement ce
// qu'ADR-0064 §2 tire de son propre échec — la logique d'arbitrage vivait dans le JSX, donc hors de
// toute épreuve, et il a fallu deux passes de revue pour la rendre juste.

import { describe, expect, it } from 'vitest'
import type { StatutPhase } from '../phases/api'
import type { PhasePublique } from './api'
import { phaseAffichee, phaseAMontrer, renduDe } from './presentation'

const phase = (id: number, ordre: number, statut: StatutPhase, type = 'poules'): PhasePublique => ({
  id,
  ordre,
  type,
  statut,
})

describe('renduDe', () => {
  it('route chaque format vers sa vue', () => {
    expect(renduDe('elimination_directe')).toBe('tableau')
    expect(renduDe('placement')).toBe('tableau')
    expect(renduDe('poules')).toBe('poules')
    expect(renduDe('suisse')).toBe('suisse')
    expect(renduDe('big_shoot_off')).toBe('big_shoot_off')
  })

  it('range ailleurs ce qui n’a pas de vue détaillée, y compris un type inconnu', () => {
    // La qualification **a** sa lecture publique (l'onglet « Classement ») et l'échauffement ne
    // produit rien par définition (§10.1) : `ailleurs` n'est pas un manque, c'est une orientation.
    expect(renduDe('qualification')).toBe('ailleurs')
    expect(renduDe('echauffement')).toBe('ailleurs')
    expect(renduDe('colline')).toBe('ailleurs')
    // ⚠️ Et un type qu'un serveur plus récent nommerait : l'appli publique reste ouverte des heures
    // sur un téléphone. Le repli affiche une ligne au lieu d'un blanc.
    expect(renduDe('format_de_2027')).toBe('ailleurs')
  })
})

describe('phaseAMontrer', () => {
  it('préfère ce qui se joue maintenant', () => {
    const choisie = phaseAMontrer([
      phase(1, 1, 'terminee'),
      phase(2, 2, 'en_cours'),
      phase(3, 3, 'a_venir'),
    ])

    expect(choisie?.id).toBe(2)
  })

  it('prend la première en cours quand plusieurs le sont', () => {
    // Deux phases d'un même créneau peuvent être en cours à la fois (deux blocs qui tirent en
    // parallèle) : on prend celle qui vient en premier dans le déroulé, pas celle que le serveur
    // liste d'abord.
    const choisie = phaseAMontrer([phase(1, 3, 'en_cours'), phase(2, 2, 'en_cours')])

    expect(choisie?.id).toBe(2)
  })

  it('retombe sur une phase en pause avant une phase terminée', () => {
    // Une phase arrêtée reste celle dont on parle dans la salle ; le classement du matin ne l'est
    // plus.
    const choisie = phaseAMontrer([phase(1, 1, 'terminee'), phase(2, 2, 'en_pause')])

    expect(choisie?.id).toBe(2)
  })

  it('à défaut, montre la DERNIÈRE phase terminée', () => {
    // À 17 h, c'est son classement qu'on vient lire — pas celui de la qualification du matin. Même
    // règle que `VueTableaux` applique déjà aux arbres.
    const choisie = phaseAMontrer([
      phase(1, 1, 'terminee', 'qualification'),
      phase(2, 2, 'terminee'),
    ])

    expect(choisie?.id).toBe(2)
  })

  it('le matin, montre la première phase à venir', () => {
    expect(phaseAMontrer([phase(2, 2, 'a_venir'), phase(1, 1, 'a_venir')])?.id).toBe(1)
  })

  it('rend null sur un déroulé vide', () => {
    expect(phaseAMontrer([])).toBeNull()
  })
})

describe('phaseAffichee', () => {
  const phases = [phase(1, 1, 'terminee'), phase(2, 2, 'en_cours')]

  it('honore le choix du spectateur', () => {
    expect(phaseAffichee(phases, 1)?.id).toBe(1)
  })

  it('retombe sur la règle quand la phase choisie a disparu', () => {
    // ⚠️ Le cas est réel : la liste se rafraîchit toute seule, et l'organisateur peut retirer une
    // phase du déroulé pendant que le spectateur la regarde. Sans ce repli, l'onglet se vidait sans
    // un mot.
    expect(phaseAffichee(phases, 99)?.id).toBe(2)
  })

  it('sans choix, applique la règle', () => {
    expect(phaseAffichee(phases, null)?.id).toBe(2)
  })
})
