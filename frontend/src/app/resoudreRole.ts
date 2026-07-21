// Résolution du rôle **effectif** de l'appareil — E00US017, ADR-0042.
//
// Fonction **pure** (pas de store, pas de DOM) : c'est le cœur risqué de l'aiguillage d'entrée, isolé
// ici pour être testé sans rendu. Elle tranche entre le **choix explicite** (marqueur `sessionRole-
// Store`) et une **session déjà ouverte**, avec une règle simple : *une session en cours prime, pour
// qu'un rechargement ne renvoie jamais sur l'écran de choix* (résilience jour J).

import type { Role } from '../shared/stores/sessionRoleStore'

export interface EtatEntree {
  // Choix explicite mémorisé à l'écran d'accueil (null tant qu'aucune porte n'a été franchie).
  roleChoisi: Role | null
  // Ce navigateur est un poste de cible (jeton de rattachement persistant).
  estPoste: boolean
  // Arrivée par le QR d'une cible (`?poste=<code>` dans l'URL).
  codePosteUrl: boolean
  // Une session admin est ouverte.
  aJetonAdmin: boolean
  // Une session scoreur est ouverte.
  aJetonScoreur: boolean
}

// Renvoie le rôle à servir, ou `null` pour afficher l'écran de choix. Ordre de précédence (ADR-0042) :
//  1. poste (physique, D-13) — inconditionnel : une tablette rattachée ou arrivée par QR reste poste ;
//  2. le choix explicite s'il est posé — c'est le geste voulu ;
//  3. un jeton admin hérité — rétro-compat d'une session d'avant cette US (ne pas rejouer le choix) ;
//  4. un jeton scoreur hérité — idem ;
//  5. rien → écran de choix.
export function resoudreRole(etat: EtatEntree): Role | null {
  if (etat.estPoste || etat.codePosteUrl) return 'tablette'
  if (etat.roleChoisi !== null) return etat.roleChoisi
  if (etat.aJetonAdmin) return 'admin'
  if (etat.aJetonScoreur) return 'scoreur'
  return null
}

// L'écran affiche-t-il l'échappatoire « Changer de rôle » ? Prédicat **pur** (même nature que
// `resoudreRole`, isolé pour être testé sans rendu). Le verrou D-13 — pas d'échappatoire d'en-tête —
// ne vaut que pour une **vraie** tablette : poste rattaché (`estPoste`) ou arrivée par QR
// (`codePosteUrl`), contrôle d'accès physique. Une tablette **seulement choisie au menu** (marqueur,
// pas encore rattachée) reste réversible — sans quoi un mauvais tap sur « Tablette » piège
// l'utilisateur sur le rattachement, sans « Détacher » (absent avant rattachement) ni retour au choix
// (correctif de revue adversariale E00US017). L'écran de choix (`role === null`) n'en a pas non plus.
export function peutChangerDeRole(
  role: Role | null,
  estPoste: boolean,
  codePosteUrl: boolean,
): boolean {
  const tabletteVerrouillee = role === 'tablette' && (estPoste || codePosteUrl)
  return role !== null && !tabletteVerrouillee
}
