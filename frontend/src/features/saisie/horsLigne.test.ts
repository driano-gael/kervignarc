// Tests du classement des échecs de saisie (E04US009, ADR-0037) — la borne d'entrée/sortie de la
// file hors-ligne. Ce qui doit aller (ou rester) en file, et ce qu'un rejeu peut retirer sans risque.

import { describe, expect, it } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import { estDejaHorsLigne, estRefusDefinitifSaisie, estRefusServeur } from './horsLigne'

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

describe('estRefusDefinitifSaisie (au rejeu)', () => {
  it('les 4xx métier non rejouables sont définitifs → retrait de la file', () => {
    expect(estRefusDefinitifSaisie(400, 'peu_importe')).toBe(true) // valeur invalide
    expect(estRefusDefinitifSaisie(403, 'peu_importe')).toBe(true) // hors-cible
    expect(estRefusDefinitifSaisie(404, 'peu_importe')).toBe(true) // blason/archer introuvable
    expect(estRefusDefinitifSaisie(422, 'peu_importe')).toBe(true) // non traitable
  })

  it('401 / 408 / 409 / 429 sont TRANSITOIRES → gardés en file (ne rien perdre)', () => {
    // 401 : serveur redémarré, jeton de poste perdu → rejeu après re-rattachement.
    expect(estRefusDefinitifSaisie(401, 'peu_importe')).toBe(false)
    expect(estRefusDefinitifSaisie(408, 'peu_importe')).toBe(false)
    // 409 : départ courant perdu au redémarrage → rejeu une fois re-fixé.
    expect(estRefusDefinitifSaisie(409, 'peu_importe')).toBe(false)
    expect(estRefusDefinitifSaisie(429, 'peu_importe')).toBe(false)
  })

  it('tout 5xx est transitoire → gardé (serveur saturé : troupeau tonitruant à la reconnexion)', () => {
    expect(estRefusDefinitifSaisie(500, 'peu_importe')).toBe(false)
    expect(estRefusDefinitifSaisie(502, 'peu_importe')).toBe(false)
    expect(estRefusDefinitifSaisie(503, 'peu_importe')).toBe(false)
  })
})

describe('estRefusDefinitifSaisie — un 409 dont la cause n’est pas transitoire (E16US020)', () => {
  it('classe `ecriture_de_role_inferieur` comme DÉFINITIF malgré son statut 409', () => {
    // ⚠️ Premier 409 définitif du produit : le rang du poste ne montera jamais. Le laisser
    // transitoire gardait la volée en file et **bloquait la tête**, donc toutes les suivantes.
    expect(estRefusDefinitifSaisie(409, 'ecriture_de_role_inferieur')).toBe(true)
  })

  it('laisse les autres 409 transitoires', () => {
    // Sans ce jumeau, marquer TOUT 409 définitif ferait perdre le cas d’origine de la liste —
    // départ courant perdu au redémarrage, re-fixé au rejeu suivant.
    expect(estRefusDefinitifSaisie(409, 'depart_courant_non_defini')).toBe(false)
  })
})
