// Tests de la présentation des doublons (E02US005, resserrée par E16US010).
//
// ⚠️ `grouperDoublons` a disparu avec l'écran dédié qu'elle titrait : le signalement vit
// désormais **sur la ligne de l'archer** (CA E16US010), donc la question n'est plus « comment
// ranger les paires en groupes » mais « que dire de CET archer ».

import { describe, expect, it } from 'vitest'
import type { Archer, Doublon } from './api'
import { signalementPour } from './presentation'

function archer(id: number): Archer {
  return {
    id,
    tournoi_id: 1,
    nom: 'Dupont',
    prenom: 'Jean',
    categorie_id: 1,
    cible: null,
    club_id: null,
    handicap_officiel: null,
    handicap_surcharge: null,
    handicap: 0,
  }
}

function doublon(niveau: string, a: number, b: number): Doublon {
  return { niveau, a: archer(a), b: archer(b) }
}

describe('signalementPour', () => {
  it('CA — un archer que rien ne rapproche n’est pas signalé', () => {
    // L'assertion qui compte : sans elle, une icône sur toutes les lignes ne dirait plus rien.
    expect(signalementPour(9, [doublon('probable', 1, 2)])).toBeNull()
    expect(signalementPour(1, [])).toBeNull()
  })

  it('CA — un archer rapproché porte le libellé de son niveau, au singulier', () => {
    // Singulier : le mot qualifie une fiche, plus un tas de fiches.
    expect(signalementPour(1, [doublon('probable', 1, 2)])?.libelle).toBe('Doublon probable')
    expect(signalementPour(3, [doublon('a_verifier', 1, 3)])?.libelle).toBe('Doublon à vérifier')
  })

  it('l’archer est trouvé des DEUX côtés de la paire', () => {
    // La paire est non orientée (`domain.doublons`) : ne regarder que `a` laisserait la moitié
    // des fiches concernées sans aucun signalement.
    expect(signalementPour(2, [doublon('probable', 1, 2)])).not.toBeNull()
  })

  it('à plusieurs paires, c’est le niveau LE PLUS CERTAIN qui l’emporte', () => {
    // Sinon le signalement le plus sûr disparaît derrière le plus douteux.
    const signalement = signalementPour(1, [doublon('a_verifier', 1, 3), doublon('probable', 1, 2)])

    expect(signalement?.niveau).toBe('probable')
    expect(signalement?.paires).toHaveLength(2)
  })

  it('un niveau inconnu du front ne fait pas DISPARAÎTRE le signalement', () => {
    // Mieux vaut « fiche à vérifier » sans qualificatif qu'un archer signalé nulle part.
    const signalement = signalementPour(1, [doublon('tres_probable', 1, 2)])

    expect(signalement).not.toBeNull()
    expect(signalement?.libelle).toBe('Fiche à vérifier')
  })
})
