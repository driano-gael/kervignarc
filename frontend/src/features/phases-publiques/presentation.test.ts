// Tests des règles de lecture de l'index des phases publiques (E05US031).
//
// Ces deux fonctions décident **ce qui s'affiche sur l'écran projeté du gymnase**, où personne ne
// peut corriger un mauvais choix : une phase mal élue y reste huit heures. C'est exactement ce
// qu'ADR-0064 §2 tire de son propre échec — la logique d'arbitrage vivait dans le JSX, donc hors de
// toute épreuve, et il a fallu deux passes de revue pour la rendre juste.

import { describe, expect, it } from 'vitest'
import type { StatutPhase } from '../phases/api'
import type { PhasePublique } from './api'
import { libelleStatut, phaseAffichee, phaseAMontrer, renduDe } from './presentation'

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
    // À 17 h, c'est son classement qu'on vient lire — pas celui du matin. Même règle que
    // `VueTableaux` applique déjà aux arbres.
    //
    // ⚠️ Les deux phases ont une **vue** : avec une `qualification` en première position, le filtre
    // `avecVue` l'écartait avant tout arbitrage et le test ne départageait plus rien (relevé à la
    // 2ᵉ passe de revue — un test à une seule candidate passe quel que soit l'ordre de préférence).
    const choisie = phaseAMontrer([phase(1, 1, 'terminee', 'suisse'), phase(2, 2, 'terminee')])

    expect(choisie?.id).toBe(2)
  })

  it('le matin, montre la première phase à venir', () => {
    expect(phaseAMontrer([phase(2, 2, 'a_venir'), phase(1, 1, 'a_venir')])?.id).toBe(1)
  })

  // ⚠️ **Le cas de la journée, et il manquait.** « Dernière terminée » n'était exercé que sur une
  // liste SANS phase à venir. Or démarrer une phase est un geste **manuel** : un créneau
  // « qualification terminée + élimination directe pas encore démarrée » est banal, et la priorité
  // inverse y affichait la qualification pendant que les duels se tiraient — sans sortie de secours
  // sur l'écran de salle. Le backend a tranché ce même arbitrage deux fois
  // (`portee.py::la_plus_courante`, `ServicePalmares._resultat`) : « à venir » passe devant.
  it('préfère une phase à venir à une phase déjà terminée', () => {
    // ⚠️ Les deux phases portent une vue, sans quoi le filtre `avecVue` réduirait la liste à une
    // seule candidate et le test rendrait le même résultat avec l'ancien ordre de préférence.
    const choisie = phaseAMontrer([
      phase(1, 1, 'terminee', 'poules'),
      phase(2, 2, 'a_venir', 'elimination_directe'),
    ])

    expect(choisie?.id).toBe(2)
  })

  // ⚠️ Les transitions ne sont pas chaînées : `demarrer` ne touche qu'une phase. Un organisateur
  // qui lance les poules sans « terminer » la qualification laissait l'écran projeté sur « les
  // résultats de la qualification se lisent dans l'onglet Classement » — vrai, mais ce n'est pas ce
  // qui se tire.
  it('ne montre pas une phase sans vue quand une autre a quelque chose à afficher', () => {
    const choisie = phaseAMontrer([
      phase(1, 1, 'en_cours', 'qualification'),
      phase(2, 2, 'en_cours', 'poules'),
    ])

    expect(choisie?.id).toBe(2)
  })

  // ⚠️ **Le cas que la première correction avait cassé** (relevé à la 2ᵉ passe de revue) : le filtre
  // « seules les phases avec vue » était appliqué AVANT les paliers de statut, si bien qu'une phase
  // à venir *avec* vue battait une phase en cours *sans* vue. C'est le déroulé de tous les matins —
  // la qualification est toujours `ordre = 1`, l'élimination directe est composée d'avance : l'écran
  // se serait ouvert sur l'ED (« l'arbre n'est pas encore monté ») pendant qu'on tirait la qualif.
  it('montre la phase EN COURS même sans vue, plutôt qu’une phase à venir qui en a une', () => {
    const choisie = phaseAMontrer([
      phase(1, 1, 'en_cours', 'qualification'),
      phase(2, 2, 'a_venir', 'elimination_directe'),
    ])

    expect(choisie?.id).toBe(1)
  })

  it('retombe sur une phase sans vue si AUCUNE n’en a — mieux vaut nommer que se taire', () => {
    const choisie = phaseAMontrer([
      phase(1, 1, 'en_cours', 'qualification'),
      phase(2, 2, 'a_venir', 'echauffement'),
    ])

    expect(choisie?.id).toBe(1)
  })

  it('rend null sur un déroulé vide', () => {
    expect(phaseAMontrer([])).toBeNull()
  })
})

describe('libelleStatut', () => {
  it('nomme les quatre statuts connus', () => {
    expect(libelleStatut('en_cours')).toBe('en cours')
    expect(libelleStatut('terminee')).toBe('terminée')
  })

  // ⚠️ Le cas que le type ne peut pas empêcher : TypeScript ne valide rien à l'exécution, et un
  // serveur plus récent peut servir un statut que ce bundle ignore. Sans repli, l'en-tête affichait
  // « Poules · » et chaque option du sélecteur perdait son statut.
  it('ne montre jamais un code technique pour un statut inconnu du bundle', () => {
    // Même doctrine que `libelleConflit` : un code d'enum ne s'affiche pas à un spectateur.
    expect(libelleStatut('statut_2027')).toBe('statut inconnu')
    expect(libelleStatut('statut_2027')).not.toMatch(/_/)
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
