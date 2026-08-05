// Tests des frappes en cours (2ᵉ passe de revue du lot « retours maquettes », 05/08/2026).
//
// L'oracle n'est pas un CA de questionnaire mais **le défaut que ce module existe pour empêcher** :
// « une volée en cours de frappe ne doit pas disparaître quand on change d'archer ». C'est de la
// non-régression sur un bloquant, le régime où l'implémenteur est le bon auteur du test (règle 9).

import { describe, expect, it } from 'vitest'
import { lireBrouillon, noterBrouillon, type Brouillons } from './brouillons'

describe('brouillons de frappe', () => {
  it('une volée commencée se relit', () => {
    const apres = noterBrouillon({}, 12, 3, ['9', '9'])
    expect(lireBrouillon(apres, 12, 3)).toEqual(['9', '9'])
  })

  it('rien n’est noté tant que rien n’est tapé', () => {
    expect(lireBrouillon({}, 12, 3)).toBeUndefined()
  })

  it('**deux archers ne partagent pas leur frappe** — c’est le défaut d’origine', () => {
    // Le tampon vivait dans un composant remonté à chaque changement d'archer : taper pour MARTIN
    // effaçait ce qu'on avait commencé pour DUPONT. Ici, les deux coexistent.
    let etat: Brouillons = noterBrouillon({}, 12, 1, ['9', '9'])
    etat = noterBrouillon(etat, 34, 1, ['7'])
    expect(lireBrouillon(etat, 12, 1)).toEqual(['9', '9'])
    expect(lireBrouillon(etat, 34, 1)).toEqual(['7'])
  })

  it('deux volées d’un même archer ne se marchent pas dessus', () => {
    // Revenir corriger la volée 3 ne doit pas écraser ce qu'on avait commencé sur la 4.
    let etat: Brouillons = noterBrouillon({}, 12, 3, ['10'])
    etat = noterBrouillon(etat, 12, 4, ['8'])
    expect(lireBrouillon(etat, 12, 3)).toEqual(['10'])
    expect(lireBrouillon(etat, 12, 4)).toEqual(['8'])
  })

  it('enregistrer efface le brouillon : la vérité repasse au serveur', () => {
    const etat = noterBrouillon(noterBrouillon({}, 12, 3, ['9', '9']), 12, 3, null)
    expect(lireBrouillon(etat, 12, 3)).toBeUndefined()
  })

  it('effacer n’emporte que la volée visée', () => {
    let etat: Brouillons = noterBrouillon({}, 12, 3, ['9'])
    etat = noterBrouillon(etat, 12, 4, ['8'])
    etat = noterBrouillon(etat, 12, 3, null)
    expect(lireBrouillon(etat, 12, 3)).toBeUndefined()
    expect(lireBrouillon(etat, 12, 4)).toEqual(['8'])
  })

  it('ne mute jamais l’état reçu — c’est de l’état React', () => {
    const avant: Brouillons = { '12:3': ['9'] }
    noterBrouillon(avant, 12, 3, ['9', '9'])
    noterBrouillon(avant, 12, 3, null)
    expect(avant).toEqual({ '12:3': ['9'] })
  })

  it('effacer un brouillon absent rend **le même objet**', () => {
    // Sans cette garde, chaque enregistrement produirait un objet neuf et ferait re-rendre toute la
    // grille des quatre archers pour rien.
    const avant: Brouillons = { '12:3': ['9'] }
    expect(noterBrouillon(avant, 99, 1, null)).toBe(avant)
  })

  it('une volée entièrement effacée reste un brouillon distinct de « pas de brouillon »', () => {
    // Nuance qui compte : tampon **vide** (l'archer a tout effacé, on ne doit pas lui réafficher la
    // volée persistée) ≠ **absence** de brouillon (on retombe sur le persisté).
    const etat = noterBrouillon({}, 12, 3, [])
    expect(lireBrouillon(etat, 12, 3)).toEqual([])
    expect(lireBrouillon(etat, 12, 4)).toBeUndefined()
  })
})
