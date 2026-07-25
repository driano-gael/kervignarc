// Tests de la construction d'URL des exports (E09US003) — logique **pure**, sans DOM ni réseau.
// Le patron testable du projet (pas de tests de composant RTL) : extraire la logique pure et la
// verrouiller ici. On vérifie que le tri est toujours joint et que le départ ne l'est que demandé.

import { describe, expect, it } from 'vitest'
import { cheminClubPaiement, cheminPlacement } from './api'

describe('cheminPlacement', () => {
  it('joint le tri, sans départ quand aucun filtre', () => {
    expect(cheminPlacement(7, { tri: 'cible', departId: null })).toBe(
      '/api/v1/tournois/7/listes/placement?tri=cible',
    )
  })

  it('joint le tri par nom', () => {
    expect(cheminPlacement(7, { tri: 'nom', departId: null })).toBe(
      '/api/v1/tournois/7/listes/placement?tri=nom',
    )
  })

  it('joint le départ quand un filtre est demandé', () => {
    expect(cheminPlacement(7, { tri: 'cible', departId: 3 })).toBe(
      '/api/v1/tournois/7/listes/placement?tri=cible&depart_id=3',
    )
  })
})

describe('cheminClubPaiement', () => {
  it('cible la route club & paiement du tournoi', () => {
    expect(cheminClubPaiement(7)).toBe('/api/v1/tournois/7/listes/club-paiement')
  })
})
