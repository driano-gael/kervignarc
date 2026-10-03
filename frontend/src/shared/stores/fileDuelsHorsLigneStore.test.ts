// La file hors-ligne des duels relit un barrage écrit avant E13US003 (une flèche par camp) : la
// file est persistée, une tablette peut en avoir un en attente au déploiement.

import { describe, expect, it } from 'vitest'
import { flechesDuBarrage, type BarrageEnFileAncien } from './fileDuelsHorsLigneStore'

const COMMUN = {
  type: 'barrage' as const,
  tournoi_id: 1,
  phase_id: 2,
  match_numero: 1,
  gagnant_designe: null,
  identifiant_saisie: 'id-b',
}

describe('flechesDuBarrage', () => {
  it('rend les listes d’un barrage écrit en listes', () => {
    expect(
      flechesDuBarrage({ ...COMMUN, fleches_haut: ['10', '9', '9'], fleches_bas: ['9', '9', '8'] }),
    ).toEqual({ haut: ['10', '9', '9'], bas: ['9', '9', '8'] })
  })

  it('relit l’ancienne forme à une flèche en listes d’une flèche', () => {
    const ancien: BarrageEnFileAncien = { ...COMMUN, fleche_haut: '10', fleche_bas: '9' }
    expect(flechesDuBarrage(ancien)).toEqual({ haut: ['10'], bas: ['9'] })
  })
})
