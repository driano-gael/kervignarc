// Tests de la discrimination des échecs de saisie de duel (E04US013, ADR-0037) — logique pure.
// Jumeau du test de la qualif : quand mettre en file, et quand un refus est définitif vs transitoire.

import { describe, expect, it } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import {
  estConditionDeRencontre,
  estDejaHorsLigne,
  estRefusDefinitif,
  estRefusServeur,
} from './horsLigne'

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
    expect(estRefusDefinitif(400, 'peu_importe')).toBe(true)
    expect(estRefusDefinitif(403, 'peu_importe')).toBe(true)
    expect(estRefusDefinitif(404, 'peu_importe')).toBe(true)
    expect(estRefusDefinitif(422, 'peu_importe')).toBe(true)
  })

  it('transitoire (à garder en file) : 401, 408, 409, 429 et tout 5xx', () => {
    expect(estRefusDefinitif(401, 'peu_importe')).toBe(false)
    expect(estRefusDefinitif(408, 'peu_importe')).toBe(false)
    expect(estRefusDefinitif(409, 'peu_importe')).toBe(false) // duel_desynchronise le temps d'un re-seed
    expect(estRefusDefinitif(429, 'peu_importe')).toBe(false)
    expect(estRefusDefinitif(500, 'peu_importe')).toBe(false)
    expect(estRefusDefinitif(503, 'peu_importe')).toBe(false)
  })
})

describe('les refus réversibles d’une recomposition de poule', () => {
  // ⚠️ Correctif de revue E05US023, né d'un autre correctif. Tant que le rejeu s'arrêtait au
  // premier refus transitoire, ces actes n'étaient jamais envoyés. Depuis qu'un 409 ne bloque plus
  // que sa rencontre, ils le sont — et leur statut (404 / 422) les faisait **retirer de la file**,
  // donc perdre. Or la cause est réversible : retirer quatre absents fait passer une phase de 12
  // rencontres à 6, et les actes des rencontres 7 à 12 redésigneront leur rencontre dès que la
  // population sera rétablie.
  it('garde en file un acte dont la rencontre a disparu (404 rencontre_introuvable)', () => {
    expect(estRefusDefinitif(404, 'rencontre_introuvable')).toBe(false)
  })

  it('garde en file un acte dont les adversaires ne sont plus résolus (422 match_non_jouable)', () => {
    expect(estRefusDefinitif(422, 'match_non_jouable')).toBe(false)
  })

  it('ne relâche pas les autres 404 / 422, qui restent définitifs', () => {
    expect(estRefusDefinitif(404, 'blason_introuvable')).toBe(true)
    expect(estRefusDefinitif(422, 'duel_verrouille')).toBe(true)
  })
})

describe('estConditionDeRencontre', () => {
  // Le rejeu ne poursuit sur les rencontres suivantes que si le refus est propre à **une**
  // rencontre. Une condition globale doit garder l'arrêt d'ensemble : insister rencontre par
  // rencontre enverrait N requêtes vouées à l'échec — et au premier 401 la session est purgée, donc
  // les suivantes partiraient anonymes.
  it('est vrai pour un conflit de composition', () => {
    expect(estConditionDeRencontre(409, 'duel_desynchronise')).toBe(true)
    expect(estConditionDeRencontre(404, 'rencontre_introuvable')).toBe(true)
    expect(estConditionDeRencontre(422, 'match_non_jouable')).toBe(true)
  })

  it('est faux pour une condition globale : session, débit, panne serveur', () => {
    expect(estConditionDeRencontre(401, 'non_authentifie')).toBe(false)
    expect(estConditionDeRencontre(429, 'trop_de_requetes')).toBe(false)
    expect(estConditionDeRencontre(503, 'indisponible')).toBe(false)
  })
})
