// Tests des règles d'affichage pures du suivi des paiements (E08US002). Oracle : les puces CA
// d'E08US002 (stories/E08-paiements.md — statut par archer, reste = dû − payé) et le comportement
// d'écran de la fiche fonctionnelle (cf. helpers purs testés `competition/format.ts`,
// `saisie/volees.ts`), pas l'implémentation. Le risque couvert : une inversion de
// seuils (« tout payé » classé « partiel », ou un bouton « régler » proposé sur un dû nul) passerait
// `tsc`/ESLint sans broncher et tromperait l'organisateur sur qui a réglé.
import { describe, expect, it } from 'vitest'

import type { RecapPaiement } from './api'
import { actionMarquage, statutPaiement } from './statut'

const recap = (du: number, paye: number): RecapPaiement => ({
  du_centimes: du,
  paye_centimes: paye,
  reste_centimes: du - paye,
})

describe('statutPaiement', () => {
  it('« neutre » quand il n’y a rien à payer (dû 0)', () => {
    expect(statutPaiement(recap(0, 0))).toBe('neutre')
  })

  it('« du » quand rien n’est payé', () => {
    expect(statutPaiement(recap(1810, 0))).toBe('du')
  })

  it('« partiel » quand une partie seulement est payée', () => {
    expect(statutPaiement(recap(1810, 810))).toBe('partiel')
  })

  it('« regle » quand le reste est nul et qu’il y avait quelque chose à payer', () => {
    // Seuil sensible : reste 0 doit primer sur payé > 0, sinon « tout payé » virerait « partiel ».
    expect(statutPaiement(recap(1810, 1810))).toBe('regle')
  })
})

describe('actionMarquage', () => {
  it('pas de bouton (null) quand le dû est nul', () => {
    expect(actionMarquage(recap(0, 0))).toBeNull()
  })

  it('« regler » tant qu’il reste à payer', () => {
    expect(actionMarquage(recap(1810, 810))).toBe('regler')
    expect(actionMarquage(recap(1810, 0))).toBe('regler')
  })

  it('« annuler » quand tout est déjà payé', () => {
    expect(actionMarquage(recap(1810, 1810))).toBe('annuler')
  })
})
