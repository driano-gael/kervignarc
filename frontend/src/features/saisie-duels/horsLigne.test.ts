// Tests de la discrimination des échecs de saisie de duel (E04US013, ADR-0037) — logique pure.
// Jumeau du test de la qualif : quand mettre en file, et quand un refus est définitif vs transitoire.

import { describe, expect, it } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import { estDejaHorsLigne, estRefusDefinitif, estRefusServeur } from './horsLigne'

describe('estDejaHorsLigne', () => {
  it('vrai seulement si le lien est déconnecté', () => {
    expect(estDejaHorsLigne('deconnecte')).toBe(true)
    expect(estDejaHorsLigne('connecte')).toBe(false)
  })
})

describe('estRefusServeur', () => {
  it('vrai pour une ErreurApi (le serveur a répondu), faux pour une panne réseau', () => {
    expect(estRefusServeur(new ErreurApi(422, 'duel_incomplet', 'Duel non tranché'))).toBe(true)
    expect(estRefusServeur(new TypeError('Failed to fetch'))).toBe(false)
  })
})

describe('estRefusDefinitif', () => {
  it('définitif : 4xx métier (400, 403, 404, 422)', () => {
    expect(estRefusDefinitif(400)).toBe(true)
    expect(estRefusDefinitif(403)).toBe(true)
    expect(estRefusDefinitif(404)).toBe(true)
    expect(estRefusDefinitif(422)).toBe(true)
  })

  it('transitoire (à garder en file) : 401, 408, 409, 429 et tout 5xx', () => {
    expect(estRefusDefinitif(401)).toBe(false)
    expect(estRefusDefinitif(408)).toBe(false)
    expect(estRefusDefinitif(409)).toBe(false) // duel_desynchronise le temps d'un re-seed
    expect(estRefusDefinitif(429)).toBe(false)
    expect(estRefusDefinitif(500)).toBe(false)
    expect(estRefusDefinitif(503)).toBe(false)
  })
})
