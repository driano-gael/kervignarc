// Tests de la règle de tête figée (E16US009) — écrits **depuis les CA**.
//
// Deux CA se croisent ici :
//
//  - P07 (E16US009) : *« ok pour les 3 premiers toujours visible, mais défilement de tous les
//    autres archers dessous »* ;
//  - A16 (E16US005) : *« les x premiers sont toujours affichés, mais le dessous du tableau a un
//    défilé jusqu'à n »* — huit sur les surfaces qu'on manipule.
//
// Et le troisième cas, celui qui n'est dans aucun questionnaire, est le **garde-fou** posé par
// ADR-0098 §2 : projeté **sans** réglage de pages, la tête retombe à zéro. Sans lui, un écran de
// salle afficherait trois lignes et rien d'autre — la régression que la revue du 05/08/2026 avait
// refusée, et la raison pour laquelle cette valeur était restée à zéro pendant trois semaines.

import { describe, expect, it } from 'vitest'
import { teteFigee } from './teteFigee'

const REGLAGE = { noms_par_page: 40, cadence_page_s: 20 }

describe('teteFigee', () => {
  it('fige les 3 premiers sur un écran projeté qui sait faire tourner le reste', () => {
    expect(teteFigee(false, 'tout', REGLAGE)).toBe(3)
  })

  it('ne fige RIEN sur un écran projeté sans réglage de pages', () => {
    // ⚠️ Le garde-fou d'ADR-0098 §2. Figer une tête sans pouvoir faire défiler le reste amputerait
    // le classement de tout ce qui suit la 3ᵉ ligne, sur la seule surface où personne ne peut agir.
    expect(teteFigee(false, 'tout', undefined)).toBe(0)
  })

  it('fige les 8 premiers sur une surface qu’on manipule', () => {
    // Huit et non trois : on y suit le haut d'une catégorie, pas seulement le podium (A16).
    expect(teteFigee(true, 'tout', undefined)).toBe(8)
  })

  it('ne fige rien sur une liste centrée sur ses propres archers', () => {
    // Figer 8 lignes sur une liste de 3 n'encadre plus rien (E16US004).
    expect(teteFigee(true, 'suivis', undefined)).toBe(0)
  })

  it('le réglage de pages n’a aucun effet sur une surface manipulable', () => {
    // La pagination est **propre à l'écran projeté** : la passer ailleurs ne doit pas déplacer la
    // tête figée, sinon deux surfaces se mettraient à dépendre d'un réglage de vidéoprojecteur.
    expect(teteFigee(true, 'tout', REGLAGE)).toBe(8)
  })
})
