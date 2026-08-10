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

// ⚠️ **Des refus dont le *statut* est définitif mais dont la *cause* ne l'est pas** — correctif de
// revue E05US023, et il est né d'un autre correctif.
//
// Tant que le rejeu s'arrêtait au premier refus transitoire, les actes situés derrière n'étaient
// jamais envoyés : ce chemin était masqué. Depuis qu'un 409 ne bloque plus que **sa** rencontre, ils
// le sont — et un `404 rencontre_introuvable` y était traité comme définitif, donc **retiré de la
// file**, score perdu contre un `console.error` que personne n'ouvrira.
//
// Or en poules, ces deux causes sont réversibles : une recomposition **peut être défaite**. Retirer
// quatre absents fait passer une phase de 12 rencontres à 6 ; les actes hors-ligne des rencontres 7
// à 12 ne désignent plus rien *aujourd'hui*, et redésigneront leur rencontre dès que la population
// sera rétablie. Les jeter, c'est perdre les scores que la recette promet noir sur blanc de garder.
const CODES_TRANSITOIRES = new Set(['rencontre_introuvable', 'match_non_jouable'])

// Au **rejeu**, un refus est-il **définitif** (rejouer n'y changera rien → on retire et on
// journalise) ? Seuls les 4xx **métier** non rejouables le sont : 400 (valeur invalide), 403
// (hors tournoi), 404 (blason introuvable), 422 (non traitable — ex. `duel_verrouille`,
// `barrage_non_requis`). Le reste — transitoires listés + 5xx — est **gardé** pour un rejeu ultérieur.
export function estRefusDefinitif(statut: number, code: string): boolean {
  return (
    statut >= 400 &&
    statut < 500 &&
    !STATUTS_TRANSITOIRES.has(statut) &&
    !CODES_TRANSITOIRES.has(code)
  )
}

// Ce refus tient-il à **cette rencontre**, ou à une condition **globale** ? Le rejeu ne poursuit sur
// les rencontres suivantes que dans le premier cas.
//
// Un 409 est propre à une rencontre : sa composition a bougé, les autres n'ont aucune raison
// d'échouer. Un 401 (session perdue, serveur redémarré), un 429 ou un 5xx valent pour **tout** ce
// que la tablette enverra : insister rencontre par rencontre ne ferait qu'envoyer N requêtes vouées
// à l'échec — et au premier 401 la session est purgée, donc les suivantes partiraient anonymes. Avec
// 30 tablettes qui redrainent après un redémarrage, c'est un troupeau lâché sur le writer unique.
export function estConditionDeRencontre(statut: number, code: string): boolean {
  return statut === 409 || CODES_TRANSITOIRES.has(code)
}
