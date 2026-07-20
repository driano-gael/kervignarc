// Tests du classement des échecs de saisie (E04US009, ADR-0037) — la borne d'entrée/sortie de la
// file hors-ligne. Ce qui doit aller (ou rester) en file, et ce qu'un rejeu peut retirer sans risque.

import { describe, expect, it } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import { estDejaHorsLigne, estRefusDefinitif, estRefusServeur } from './horsLigne'

describe('estDejaHorsLigne', () => {
  it('lien tombé → on se sait hors-ligne (court-circuit, mise en file directe)', () => {
    expect(estDejaHorsLigne('deconnecte')).toBe(true)
  })

  it('lien connecté ou en cours → on tente le POST', () => {
    expect(estDejaHorsLigne('connecte')).toBe(false)
    expect(estDejaHorsLigne('connexion')).toBe(false)
  })
})

describe('estRefusServeur (à la saisie)', () => {
  it('une ErreurApi = le serveur a répondu un refus → vraie erreur, jamais mise en file', () => {
    expect(estRefusServeur(new ErreurApi(403, 'hors_cible', 'Hors cible'))).toBe(true)
  })

  it('une panne réseau (le fetch rejette, TypeError) n’est pas un refus serveur → mise en file', () => {
    expect(estRefusServeur(new TypeError('Failed to fetch'))).toBe(false)
  })
})

describe('estRefusDefinitif (au rejeu)', () => {
  it('les 4xx métier non rejouables sont définitifs → retrait de la file', () => {
    expect(estRefusDefinitif(400)).toBe(true) // valeur invalide
    expect(estRefusDefinitif(403)).toBe(true) // hors-cible
    expect(estRefusDefinitif(404)).toBe(true) // blason/archer introuvable
    expect(estRefusDefinitif(422)).toBe(true) // non traitable
  })

  it('401 / 408 / 409 / 429 sont TRANSITOIRES → gardés en file (ne rien perdre)', () => {
    // 401 : serveur redémarré, jeton de poste perdu → rejeu après re-rattachement.
    expect(estRefusDefinitif(401)).toBe(false)
    expect(estRefusDefinitif(408)).toBe(false)
    // 409 : départ courant perdu au redémarrage → rejeu une fois re-fixé.
    expect(estRefusDefinitif(409)).toBe(false)
    expect(estRefusDefinitif(429)).toBe(false)
  })

  it('tout 5xx est transitoire → gardé (serveur saturé : troupeau tonitruant à la reconnexion)', () => {
    expect(estRefusDefinitif(500)).toBe(false)
    expect(estRefusDefinitif(502)).toBe(false)
    expect(estRefusDefinitif(503)).toBe(false)
  })
})
