// Classement des échecs de saisie de duel pour la file hors-ligne (E04US013, ADR-0037) — logique
// pure, testée en node. Jumeau de `features/saisie/horsLigne` (2ᵉ occurrence, règle 12 : dupliqué,
// pas extrait avant un 3ᵉ cas). C'est la **borne** de la résilience : décider quand un acte va en
// file, et — au rejeu — quand un refus est **définitif** (à retirer) ou **transitoire** (à garder,
// « ne rien perdre » prime).

import { ErreurApi } from '../../shared/api/client'
import type { StatutConnexion } from '../../shared/stores/connexionStore'

// Court-circuit à la saisie : si le lien WebSocket est **déjà** tombé, on se sait hors-ligne et on
// met en file sans tenter un POST qui pendrait (pas de timeout sur `fetch`).
export function estDejaHorsLigne(statut: StatutConnexion): boolean {
  return statut === 'deconnecte'
}

// À la saisie, un échec est-il un **refus du serveur** (il a répondu, `ErreurApi`) plutôt qu'une
// **panne réseau** (le `fetch` a rejeté) ? Un refus serveur est une **vraie erreur** montrée au
// scoreur (il corrige) ; il n'a pas de sens à mettre en file. Une panne réseau, elle, va en file.
export function estRefusServeur(erreur: unknown): boolean {
  return erreur instanceof ErreurApi
}

// Codes que le serveur peut renvoyer **transitoirement** — un rejeu ultérieur peut réussir, donc on
// NE retire PAS l'acte de la file : 401 (session scoreur perdue, ex. serveur redémarré → à rouvrir),
// 408 (timeout), 409 (conflit d'état, ex. `duel_desynchronise` le temps d'un re-seed), 429 (débit).
// Tout **5xx** est transitoire aussi (writer unique saturé — reconnexion de masse). Un score gardé
// et rejoué plus tard vaut mieux qu'un score perdu en silence.
const STATUTS_TRANSITOIRES = new Set([401, 408, 409, 429])

// Au **rejeu**, un refus est-il **définitif** (rejouer n'y changera rien → on retire et on
// journalise) ? Seuls les 4xx **métier** non rejouables le sont : 400 (valeur invalide), 403
// (hors tournoi), 404 (blason introuvable), 422 (non traitable — ex. `duel_verrouille`,
// `barrage_non_requis`). Le reste — transitoires listés + 5xx — est **gardé** pour un rejeu ultérieur.
export function estRefusDefinitif(statut: number): boolean {
  return statut >= 400 && statut < 500 && !STATUTS_TRANSITOIRES.has(statut)
}
