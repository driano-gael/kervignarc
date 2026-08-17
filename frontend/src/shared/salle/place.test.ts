// Tests du libellé compact des places d'une rencontre (E05US031).
//
// Ce fichier naît d'un défaut relevé par **trois axes de revue** sur la même ligne : le rendu public
// n'affichait que la cible de la **première** place, si bien qu'une rencontre à cheval sur deux
// cibles envoyait le second archer au mauvais endroit — sur l'écran projeté du gymnase, celui que
// personne ne peut corriger.
//
// ⚠️ **Le cas n'a rien d'exotique**, et c'est ce qui le rend dangereux : `GabaritSalle` autorise une
// capacité **variable par cible** (1 à 4), et un bloc de couloirs est contigu dans la salle *mise à
// plat*, pas sur une cible. Il suffit d'une cible à 1 ou 3 couloirs pour que la parité se décale.
// Le dépôt avait déjà payé ce défaut deux fois avant celle-ci (`SaisiePoules`, `decrirePlaces`).

import { describe, expect, it } from 'vitest'
import { libelleCibles, type Place } from './place'

describe('libelleCibles', () => {
  it('groupe les deux couloirs quand ils sont sur la même cible', () => {
    const paire: [Place, Place] = [
      [3, 'A'],
      [3, 'B'],
    ]

    expect(libelleCibles(paire)).toBe('Cible 3A/B')
  })

  it('nomme les DEUX cibles quand la rencontre est à cheval', () => {
    // Une cible à 3 couloirs décale la parité : la paire suivante commence sur la cible d'après.
    const paire: [Place, Place] = [
      [1, 'C'],
      [2, 'A'],
    ]

    // Ce que rendait la première version : « Cible 1C/A » — le second archer envoyé sur la cible 1.
    expect(libelleCibles(paire)).not.toBe('Cible 1C/A')
    expect(libelleCibles(paire)).toBe('Cibles 1C et 2A')
  })

  it('ne perd jamais la seconde cible, quelles que soient les places', () => {
    // Garde-fou de forme : le libellé doit toujours porter les deux numéros de cible.
    const paire: [Place, Place] = [
      [7, 'D'],
      [8, 'A'],
    ]

    expect(libelleCibles(paire)).toContain('7')
    expect(libelleCibles(paire)).toContain('8')
  })
})
