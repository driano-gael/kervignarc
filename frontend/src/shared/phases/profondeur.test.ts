// La logique du tri-état « jusqu'où classer » (E06US006, ADR-0070) — sans DOM.
//
// Ces trois fonctions sont le cœur du réglage, et c'est leur duplication de fait (un état dans le
// composant, un autre dans chaque parent) qui a produit l'unique bloquant de l'US. Les tester ici
// coûte trois lignes par cas et couvre les deux écrans à la fois.

import { describe, expect, it } from 'vitest'
import {
  decrireProfondeur,
  depuisProfondeur,
  estValide,
  versProfondeur,
  PROFONDEUR_AU_PRESET,
  RANGS_DU_PODIUM,
} from './profondeur'

describe('depuisProfondeur', () => {
  it('lit une phase non réglée comme le preset', () => {
    expect(depuisProfondeur(null)).toEqual(PROFONDEUR_AU_PRESET)
  })

  it('lit un classement intégral', () => {
    expect(depuisProfondeur({ nom: 'un_vers_n', jusqu_au: null })).toEqual({ mode: 'integral' })
  })

  it('lit un top N et garde son rang', () => {
    expect(depuisProfondeur({ nom: 'top_n', jusqu_au: 8 })).toEqual({ mode: 'top', seuil: '8' })
  })

  it('retombe sur le preset du podium si le rang manque', () => {
    // Ne peut venir que d'une réponse serveur incohérente ; mieux vaut une pré-saisie plausible
    // qu'un champ vide qui bloquerait le formulaire sans que l'organisateur ait rien fait.
    expect(depuisProfondeur({ nom: 'top_n', jusqu_au: null })).toEqual({
      mode: 'top',
      seuil: String(RANGS_DU_PODIUM),
    })
  })
})

describe('versProfondeur', () => {
  it('n’envoie rien pour le preset — et surtout pas un podium explicite', () => {
    // `null` ≠ `{nom:'top_n', jusqu_au:4}` : les deux produisent le même tournoi, mais seul le
    // premier laisse la phase suivre son preset au lieu d'inscrire un choix qu'on n'a pas fait.
    expect(versProfondeur({ mode: 'preset' })).toBeNull()
  })

  it('envoie le classement intégral sans rang d’arrêt', () => {
    expect(versProfondeur({ mode: 'integral' })).toEqual({ nom: 'un_vers_n', jusqu_au: null })
  })

  it('envoie le rang d’arrêt d’un top N', () => {
    expect(versProfondeur({ mode: 'top', seuil: '16' })).toEqual({ nom: 'top_n', jusqu_au: 16 })
  })

  it.each(['', '  ', '0', '-3', 'huit', '2.5'])('refuse le rang d’arrêt « %s »', (seuil) => {
    // `undefined` = illisible : l'appelant bloque sa soumission, il ne transmet jamais cette
    // valeur — un `undefined` transmis signifierait « efface le réglage » côté serveur.
    expect(versProfondeur({ mode: 'top', seuil })).toBeUndefined()
    expect(estValide({ mode: 'top', seuil })).toBe(false)
  })

  it('tient l’aller-retour sur les trois modes', () => {
    for (const profondeur of [
      null,
      { nom: 'un_vers_n', jusqu_au: null } as const,
      { nom: 'top_n', jusqu_au: 8 } as const,
    ]) {
      expect(versProfondeur(depuisProfondeur(profondeur))).toEqual(profondeur)
    }
  })
})

describe('decrireProfondeur', () => {
  // Affiché sur la ligne de phase des **deux** écrans de composition ; aucun des deux ne l'assertait.
  it('nomme le classement intégral', () => {
    expect(decrireProfondeur({ nom: 'un_vers_n', jusqu_au: null })).toBe('classement intégral')
  })

  it('nomme le rang où le classement s’arrête', () => {
    expect(decrireProfondeur({ nom: 'top_n', jusqu_au: 8 })).toBe("classé jusqu'au 8ᵉ")
  })
})
