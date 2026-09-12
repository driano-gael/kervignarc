// Classement des échecs de saisie pour la file hors-ligne (E04US009, ADR-0037) — logique pure,
// testée en node. C'est la **borne d'entrée et de sortie** de la résilience : décider quand une
// saisie va en file, et — au rejeu — quand un refus est **définitif** (à retirer) ou **transitoire**
// (à garder, « ne rien perdre » prime). Isolé du hook pour être testable sans DOM (miroir de `rejeu`).

import { ErreurApi } from '../../shared/api/client'
import type { StatutConnexion } from '../../shared/stores/connexionStore'

// Court-circuit à la saisie : si le lien WebSocket est **déjà** tombé, on se sait hors-ligne et on
// met en file sans tenter un POST qui pendrait (pas de timeout sur `fetch`).
export function estDejaHorsLigne(statut: StatutConnexion): boolean {
  return statut === 'deconnecte'
}

// À la saisie (1ʳᵉ tentative), un échec est-il un **refus du serveur** (il a répondu) plutôt qu'une
// **panne réseau** (le `fetch` a rejeté) ? Un refus serveur est une **vraie erreur** montrée au
// marqueur (il ressaisit) ; il n'a pas de sens à mettre en file — le serveur a tranché, ici et
// maintenant. Une panne réseau, elle, va en file. (`fetchJson` ne lève `ErreurApi` que sur réponse
// non-2xx ; un rejet réseau remonte une `TypeError`.)
export function estRefusServeur(erreur: unknown): boolean {
  return erreur instanceof ErreurApi
}

// Codes que le serveur peut renvoyer **transitoirement** — un rejeu ultérieur peut réussir, donc on
// NE retire PAS la saisie de la file : 401 (session/jeton perdu, ex. serveur redémarré → re-rattachement),
// 408 (timeout), 409 (conflit d'état, ex. départ courant perdu au redémarrage → re-fixé), 429 (débit).
// Tout **5xx** est transitoire aussi (serveur saturé — cas du « troupeau tonitruant » à la reconnexion
// de masse). Un score gardé et rejoué plus tard vaut infiniment mieux qu'un score perdu en silence.
const STATUTS_TRANSITOIRES = new Set([401, 408, 409, 429])

// ⚠️ **Un refus au *statut* transitoire dont la *cause* ne l'est pas** — correctif de revue
// E16US020, jumeau inversé de `CODES_TRANSITOIRES` côté duels.
//
// `ecriture_de_role_inferieur` est le **premier 409 définitif du produit** : le rang du poste ne
// montera jamais, et l'écriture d'en face est durable. Le laisser transitoire gardait la volée en
// file, et comme le rejeu **s'arrête au premier refus gardé**, toutes les volées enfilées derrière
// ne partaient plus jamais — file persistée en `localStorage`, donc survivant au rechargement.
const CODES_DEFINITIFS = new Set(['ecriture_de_role_inferieur'])

// Au **rejeu**, un refus est-il **définitif** (rejouer n'y changera rien → on retire de la file et on
// journalise) ? Seuls les 4xx **métier** non rejouables le sont : 400 (valeur invalide), 403
// (hors-cible), 404 (blason/archer introuvable), 422 (non traitable). Tout le reste — transitoires
// listés + 5xx — est **gardé en file** pour un rejeu ultérieur.
export function estRefusDefinitif(statut: number, code: string): boolean {
  if (CODES_DEFINITIFS.has(code)) return true
  return statut >= 400 && statut < 500 && !STATUTS_TRANSITOIRES.has(statut)
}
