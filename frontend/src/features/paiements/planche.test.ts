// Tests des règles pures de la planche A17 (E17US012) — écrits depuis le CA :
// `stories/E17-fidelite-aux-maquettes.md`, E17US012, puce « A17 » (bandeau de totaux, ancienneté)
// et son arbitrage du 26/09/2026 (une inscription sans date s'affiche « date inconnue »).
import { describe, expect, it } from 'vitest'

import type { LignePaiementArcher } from './api'
import { libelleDepuis, totauxDuBandeau } from './planche'

const ligne = (du: number, paye: number): LignePaiementArcher => ({
  archer_id: 1,
  nom: 'MARTIN',
  prenom: 'Sophie',
  club_id: null,
  recap: { du_centimes: du, paye_centimes: paye, reste_centimes: du - paye },
  club: null,
  categorie: 'Senior 1 Femme',
  dette: null,
})

describe('totauxDuBandeau (A17)', () => {
  it('attendu, encaissé, restant dû et archers concernés sur tout le tournoi', () => {
    const totaux = totauxDuBandeau([ligne(1400, 1400), ligne(2400, 1000), ligne(1000, 0)])
    expect(totaux).toEqual({
      attendu_centimes: 4800,
      encaisse_centimes: 2400,
      restant_du_centimes: 2400,
      archers_concernes: 2,
    })
  })

  it('un archer qui ne doit rien (créneau gratuit, ou pas inscrit) n’est pas « concerné »', () => {
    expect(totauxDuBandeau([ligne(0, 0), ligne(1400, 1400)]).archers_concernes).toBe(0)
  })

  it('une liste vide totalise zéro partout', () => {
    expect(totauxDuBandeau([])).toEqual({
      attendu_centimes: 0,
      encaisse_centimes: 0,
      restant_du_centimes: 0,
      archers_concernes: 0,
    })
  })
})

describe('libelleDepuis (A17 · DEPUIS)', () => {
  it('une dette datée se lit « inscription du JJ/MM », comme sur la planche', () => {
    // Midi UTC : le même jour dans tous les fuseaux d'Europe, le test ne dépend pas de la machine.
    expect(libelleDepuis({ depuis: '2026-11-02T12:00:00Z' })).toBe('inscription du 02/11')
  })

  it('une dette sans date (inscription d’avant la migration) se dit « date inconnue »', () => {
    expect(libelleDepuis({ depuis: null })).toBe('date inconnue')
  })

  it('sans dette, rien à dater — mais jamais une case vide', () => {
    expect(libelleDepuis(null)).toBe('—')
  })
})
