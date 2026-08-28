// La jointure **étape → phase de créneau** par le rang, au pilotage (E16US002).
//
// ⚠️ **Livrée sans aucune garde**, relevé en 2ᵉ passe : `features/suivi-deroule/` ne contenait pas
// un test, et rien ne montait `PilotageCreneau` — l'écran où l'on **démarre** et **termine** une
// phase, donc le seul où confondre deux qualifications homonymes coûte un mauvais classement
// publié. La jointure se fait par `ordre`, clé partagée entre une étape et ses instances (ADR-0076
// §3, `application/phases.py`).

import { describe, expect, it } from 'vitest'

import type { EtapeDeroule } from '../phases/api'
import { titresParOrdre } from './titres'

function etape(ordre: number, titre: string | null): EtapeDeroule {
  return {
    id: ordre,
    tournoi_id: 1,
    ordre,
    type: 'qualification',
    sources: [],
    effectif: null,
    barrage_jusqu_au: null,
    profondeur: null,
    poules: null,
    big_shoot_off: null,
    suisse: null,
    colline: null,
    decoupage: null,
    nb_volees: null,
    arrets: [],
    titre,
  }
}

describe('titresParOrdre', () => {
  it('rend le titre de chaque étape sous son rang', () => {
    const titres = titresParOrdre([
      etape(1, 'Qualification jeunes'),
      etape(2, 'Qualification adultes'),
    ])

    expect(titres.get(1)).toBe('Qualification jeunes')
    expect(titres.get(2)).toBe('Qualification adultes')
  })

  it('rend null pour une étape que l’organisateur n’a pas nommée', () => {
    // Le cas de **tous** les déroulés existants : la ligne doit alors retomber sur le libellé du
    // type, exactement comme avant l'US.
    expect(titresParOrdre([etape(1, null)]).get(1)).toBeNull()
  })

  it('rend une map vide tant que les étapes ne sont pas chargées', () => {
    // `usePhases` rend `undefined` au premier rendu. Sans ce cas, un `.map` sur `undefined`
    // ferait planter l'écran de pilotage au montage — sur un écran du jour J.
    expect(titresParOrdre(undefined).size).toBe(0)
  })

  it('n’invente aucun titre pour un rang sans étape correspondante', () => {
    // Fenêtre réelle : une étape vient d'être supprimée et le créneau porte encore sa phase, ou
    // les deux requêtes n'ont pas atterri ensemble. La ligne doit retomber sur son type, pas
    // hériter du titre du voisin.
    const titres = titresParOrdre([etape(1, 'Qualification jeunes')])

    expect(titres.get(2)).toBeUndefined()
  })
})
