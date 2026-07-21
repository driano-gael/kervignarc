// Tests de la dérivation d'affichage de la complétude (E12US005) — logique pure, testée en node
// (comme `supervision/etat.test.ts`). On couvre le rendu d'une ligne (décompte + unité) et surtout la
// **composition du message de confirmation** avant de terminer : c'est la protection de la seule
// action irréversible (E01US002), elle doit chiffrer ce qui reste (`P-4`) et dire ce qui se fige.

import { describe, expect, it } from 'vitest'
import type { Completude, LigneCompletude } from './api'
import { afficheEtat, detailLigne, messageConfirmationTerminer } from './presentation'

function ligne(partial: Partial<LigneCompletude> & Pick<LigneCompletude, 'cle'>): LigneCompletude {
  return {
    libelle: partial.cle,
    etat: 'ok',
    fait: null,
    total: null,
    ...partial,
  }
}

function completude(over: Partial<Completude> = {}): Completude {
  return {
    sportif: [
      ligne({ cle: 'qualification', etat: 'ok', fait: 30, total: 30 }),
      ligne({ cle: 'phases_eliminatoires', etat: 'a_venir' }),
      ligne({ cle: 'classement', etat: 'ok' }),
    ],
    hors_sportif: [ligne({ cle: 'paiements', etat: 'ok', fait: 156, total: 156 })],
    sportif_complet: true,
    ...over,
  }
}

describe('afficheEtat', () => {
  it('alerte → libellé « À finir » (rendu en ambre côté CSS, pas rouge — DV-03)', () => {
    expect(afficheEtat('alerte')).toEqual({ classe: 'alerte', libelle: 'À finir' })
  })

  it('à venir → état séquencé, neutre', () => {
    expect(afficheEtat('a_venir')).toEqual({ classe: 'a_venir', libelle: 'À venir' })
  })
})

describe('detailLigne', () => {
  it('qualification → décompte suffixé « cibles »', () => {
    expect(detailLigne(ligne({ cle: 'qualification', fait: 28, total: 30 }))).toBe('28/30 cibles')
  })

  it('paiements → décompte nu (sans unité)', () => {
    expect(detailLigne(ligne({ cle: 'paiements', fait: 144, total: 156 }))).toBe('144/156')
  })

  it('ligne sans décompte (phases, classement) → pas de détail', () => {
    expect(detailLigne(ligne({ cle: 'phases_eliminatoires', etat: 'a_venir' }))).toBeNull()
  })
})

describe('messageConfirmationTerminer', () => {
  it('sportif complet → seulement l’implication, sans alarme', () => {
    const message = messageConfirmationTerminer(completude())
    expect(message).toContain('figera le sportif')
    expect(message).toContain('paiements resteront modifiables')
    expect(message).toContain('Terminer le tournoi ?')
    expect(message).not.toContain('quand même')
  })

  it('qualification et paiements incomplets → chiffre ce qui reste + « quand même »', () => {
    const message = messageConfirmationTerminer(
      completude({
        sportif: [
          ligne({ cle: 'qualification', etat: 'alerte', fait: 28, total: 30 }),
          ligne({ cle: 'phases_eliminatoires', etat: 'a_venir' }),
          ligne({ cle: 'classement', etat: 'en_attente' }),
        ],
        hors_sportif: [ligne({ cle: 'paiements', etat: 'alerte', fait: 144, total: 156 })],
        sportif_complet: false,
      }),
    )
    expect(message).toContain('2 cible(s) de qualification ne sont pas terminées')
    expect(message).toContain('12 archer(s) n’ont pas réglé')
    expect(message).toContain('Terminer quand même ?')
  })

  it('les phases éliminatoires « à venir » ne sont jamais listées comme un manque', () => {
    const message = messageConfirmationTerminer(
      completude({
        sportif: [
          ligne({ cle: 'qualification', etat: 'ok', fait: 30, total: 30 }),
          ligne({ cle: 'phases_eliminatoires', etat: 'a_venir' }),
          ligne({ cle: 'classement', etat: 'ok' }),
        ],
        sportif_complet: true,
      }),
    )
    expect(message).not.toContain('phase')
    expect(message).not.toContain('éliminatoire')
  })
})
