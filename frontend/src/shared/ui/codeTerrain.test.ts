// Tests de la normalisation d'un code de terrain (retour maquettes du 04/08/2026, S01).
//
// Les cas dérivent de la demande — *« un pavé de saisie qui ne laisse pas de caractère non
// accessible »* — et de l'alphabet que le serveur documente déjà (`infrastructure/postes/codes.py` :
// « 32 symboles sans les confondables I, O, 0, 1 »).

import { describe, expect, it } from 'vitest'
import { ALPHABET_CODE, LONGUEUR_CODE, normaliserCode } from './codeTerrain'

describe('alphabet des codes', () => {
  it('exclut les quatre confondables, comme le serveur', () => {
    for (const confondable of ['I', 'O', '0', '1']) {
      expect(ALPHABET_CODE).not.toContain(confondable)
    }
  })

  it('compte 32 symboles', () => {
    expect(ALPHABET_CODE).toHaveLength(32)
  })
})

describe('normaliserCode', () => {
  it('met en majuscules — un code dicté se note souvent en minuscules', () => {
    expect(normaliserCode('ab2cd3')).toBe('AB2CD3')
  })

  it('retire ce qu’un collage traîne : espaces, tirets, ponctuation', () => {
    expect(normaliserCode('AB2 - CD3')).toBe('AB2CD3')
  })

  it('retire les confondables **sans les corriger**', () => {
    // Traduire `O` en `0` serait une supposition, et `0` n'existe pas plus que `O` dans l'alphabet :
    // il n'y a rien vers quoi corriger. On retire, le serveur tranche.
    expect(normaliserCode('OI01')).toBe('')
    expect(normaliserCode('AOB')).toBe('AB')
  })

  it('borne à la longueur d’un code', () => {
    expect(normaliserCode('ABCDEFGHJK')).toHaveLength(LONGUEUR_CODE)
  })

  it('laisse passer un code déjà propre, inchangé', () => {
    expect(normaliserCode('ZK7M4P')).toBe('ZK7M4P')
  })

  it('rend une chaîne vide plutôt que de planter sur une entrée vide', () => {
    expect(normaliserCode('')).toBe('')
  })
})
