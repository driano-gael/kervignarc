// Tests des fonctions pures du journal d'audit (E16US016) — filtre, repli et libellés.
//
// Pures, donc éprouvables sans rendu : c'est ici que vit la logique du CA « le journal se
// consulte », l'écran n'en étant que l'habillage.

import { describe, expect, it } from 'vitest'

import type { EntreeAudit } from './api'
import {
  actionsPresentes,
  estCorrective,
  filtrer,
  heureLocale,
  libelleAction,
} from './presentation'

function entree(partiel: Partial<EntreeAudit>): EntreeAudit {
  return {
    id: 1,
    tournoi_id: 1,
    action: 'validation',
    auteur: 'DURAND Jean',
    horodatage: '2026-09-18T08:12:04Z',
    objet: 'Série 1 — cible 4A',
    avant: null,
    apres: null,
    ...partiel,
  }
}

describe('libelleAction', () => {
  it('traduit les actes connus', () => {
    expect(libelleAction('correction_score')).toBe('Correction')
  })

  it('rend le slug brut pour un acte inconnu, plutôt qu’une case vide', () => {
    // ⚠️ Garde-fou du registre jumeau : `ActionAuditee` peut gagner un membre sans que cette
    // table le sache — les deux listes sont dans deux langages. Côté serveur, le jumeau est
    // gardé par une assertion d'exhaustivité (`test_tableur_palmares.py`) ; ici c'est le repli.
    expect(libelleAction('nouvel_acte')).toBe('nouvel_acte')
  })
})

describe('estCorrective', () => {
  it('reconnaît une correction et une annulation', () => {
    expect(estCorrective(entree({ action: 'correction_score' }))).toBe(true)
    expect(estCorrective(entree({ action: 'annulation_validation' }))).toBe(true)
  })

  it('ne compte pas une validation', () => {
    expect(estCorrective(entree({}))).toBe(false)
  })
})

describe('filtrer', () => {
  const journal = [
    entree({ id: 1, auteur: 'LE GUEN Anne', objet: 'Série 1' }),
    entree({
      id: 2,
      action: 'correction_score',
      auteur: 'ROUX Ana',
      objet: 'Série 2',
      avant: '8',
      apres: '9',
    }),
    entree({ id: 3, action: 'forfait', auteur: 'MOREAU Yves', objet: 'Cible 14' }),
  ]

  it('sans critère, rend tout', () => {
    expect(filtrer(journal, '', '')).toHaveLength(3)
  })

  it('filtre par type d’acte', () => {
    expect(filtrer(journal, 'forfait', '').map((e) => e.id)).toEqual([3])
  })

  it('replie bien les accents, et NE replie PAS ce qui n’en est pas', () => {
    // ⚠️ Ancrage posé en 2ᵉ passe : la propriété n'était couverte par rien, et le passage de
    // `[̀-ͯ]` à une propriété Unicode a été fait sans test. `\p{Diacritic}` retirait
    // aussi `^` et `` ` `` — une recherche sur `^` aurait alors matché toutes les lignes.
    const accentue = [entree({ id: 9, auteur: 'LE GUÉN Anne' })]
    expect(filtrer(accentue, '', 'le guen')).toHaveLength(1)
    expect(filtrer(accentue, '', 'le guén')).toHaveLength(1)
    expect(filtrer(accentue, '', '^')).toHaveLength(0)
  })

  it('cherche dans l’auteur en repliant casse et accents', () => {
    // « leguen » sans espace ne doit PAS trouver « LE GUEN » — on replie les accents, on ne
    // supprime pas les espaces : ce serait une autre règle, non demandée.
    expect(filtrer(journal, '', 'le guen').map((e) => e.id)).toEqual([1])
    expect(filtrer(journal, '', 'ROUX').map((e) => e.id)).toEqual([2])
  })

  it('cherche aussi dans l’objet et dans l’avant/après', () => {
    expect(filtrer(journal, '', 'cible 14').map((e) => e.id)).toEqual([3])
    expect(filtrer(journal, '', '9').map((e) => e.id)).toEqual([2])
  })

  it('combine le type d’acte et la recherche', () => {
    expect(filtrer(journal, 'correction_score', 'ana').map((e) => e.id)).toEqual([2])
    expect(filtrer(journal, 'forfait', 'ana')).toHaveLength(0)
  })
})

describe('actionsPresentes', () => {
  it('ne propose que les actes réellement présents, triés sur leur libellé', () => {
    // ⚠️ Proposer les huit actes du domaine ferait choisir « Remboursement » sur un journal qui
    // n'en contient aucun : le tableau se viderait sans que rien n'explique pourquoi.
    const presentes = actionsPresentes([
      entree({ action: 'validation' }),
      entree({ action: 'forfait' }),
      entree({ action: 'validation' }),
    ])
    expect(presentes).toEqual(['forfait', 'validation'])
  })
})

describe('heureLocale', () => {
  it('rend l’horodatage tel quel s’il est illisible, sans planter', () => {
    expect(heureLocale('pas une date')).toBe('pas une date')
  })

  it('rend une date lisible pour un instant UTC valide', () => {
    expect(heureLocale('2026-09-18T08:12:04Z')).toMatch(/2026/)
  })
})
