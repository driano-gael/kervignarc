// Résumé d'un gabarit (E01US007, libellés révisés par E16US001).
//
// Ces cas fixent deux choses que la seule lecture du code ne garantit pas : l'accord du pluriel se
// fait sur le **plus grand** plafond (celui que porte le « jusqu'à »), et le mot « jusqu'à » ne
// disparaît pas — la capacité d'une cible est un **plafond**, jamais un effectif.

import { describe, expect, it } from 'vitest'
import type { Gabarit } from './api'
import { decrire } from './format'

// Un gabarit réduit à ce que `decrire` lit : le nombre de cibles et leurs capacités.
function gabarit(capacites: number[]): Gabarit {
  return {
    id: 1,
    nom: 'Salle municipale',
    nb_cibles: capacites.length,
    tournoi_id: null,
    cibles: capacites.map((capacite, index) => ({
      index: index + 1,
      capacite,
      positions: Array.from({ length: capacite }, (_, rang) => String.fromCharCode(65 + rang)),
    })),
  }
}

describe('decrire', () => {
  it('garde le singulier quand le plafond unique vaut 1', () => {
    // Seul cas où l'accord bascule : une cible d'un couloir n'a pas de « couloirs ».
    expect(decrire(gabarit([1, 1, 1]))).toBe("3 cibles · jusqu'à 1 couloir/cible")
  })

  it('passe au pluriel dès que le plafond unique dépasse 1', () => {
    // Démontre que « un seul plafond » ne suffit pas à conclure au singulier.
    expect(decrire(gabarit([4, 4]))).toBe("2 cibles · jusqu'à 4 couloirs/cible")
  })

  it('accorde sur le plus grand plafond, même quand la liste commence à 1', () => {
    // Le piège : accorder sur le premier plafond écrirait « 1/2/4 couloir/cible ».
    expect(decrire(gabarit([1, 2, 4, 2]))).toBe("4 cibles · jusqu'à 1/2/4 couloirs/cible")
  })

  it('dédoublonne et trie les plafonds', () => {
    expect(decrire(gabarit([4, 2, 4, 2]))).toBe("4 cibles · jusqu'à 2/4 couloirs/cible")
  })

  it('accorde aussi le mot « cible » au singulier', () => {
    expect(decrire(gabarit([2]))).toBe("1 cible · jusqu'à 2 couloirs/cible")
  })
})
