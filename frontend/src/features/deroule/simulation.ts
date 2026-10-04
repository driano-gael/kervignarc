// Les décisions du panneau « Faire tourner le format » (E01US024) — logique pure, aucun React.

import { MOTEUR_SAIT_JOUER } from '../../shared/phases/catalogue'
import { EFFECTIF_MAX, type Diagnostic, type LigneClassement, type PhaseSimulee } from './api'
import { lireEntier } from './sequence'

/** L'effectif simulé, borné **comme le serveur** (`EFFECTIF_MAX`).
 *
 * ⚠️ La borne serveur a été ajoutée sur `GET …/diagnostic` sans être propagée ici dans un premier
 * jet : saisir `300` revenait en 400 « Requête invalide. » et faisait **disparaître tout le
 * schéma**, verdict et anomalies compris, derrière un message qui ne disait pas la borne. Avant
 * l'ajout, ce cas rendait un diagnostic valide : régression introduite par le correctif lui-même.
 */
export function analyserEffectif(saisi: string): number | null {
  const valeur = lireEntier(saisi)
  if (typeof valeur !== 'number' || valeur > EFFECTIF_MAX) return null
  return valeur
}

/** Pourquoi le bouton « Simuler » est refusé, ou `null` s'il est offert. */
export function motifEmpechementSimulation(
  diagnostic: Diagnostic | undefined,
  effectif: number | null,
): string | null {
  // Le serveur reste l'autorité (400 `format_non_simulable`) ; ce garde évite seulement d'offrir un
  // bouton dont on sait qu'il sera refusé — même parti que `TYPES_SANS_CLASSEMENT`.
  if (diagnostic === undefined) return 'Le déroulé est en cours de calcul.'
  if (!diagnostic.applicable) {
    return 'On ne simule pas un déroulé qu’aucun tournoi ne pourrait recevoir : corrigez d’abord les points bloquants.'
  }
  if (!diagnostic.blocs.some((bloc) => bloc.type === 'qualification')) {
    return 'Ce format ne décrit aucune qualification : la simulation n’a alors aucun barème d’où tirer des scores. Le format reste applicable à un tournoi.'
  }
  if (effectif === null || effectif < 2 || effectif > EFFECTIF_MAX) {
    return `Indiquez un effectif entre 2 et ${EFFECTIF_MAX} archers pour lancer la simulation.`
  }
  return null
}

/** La note d'écart d'une phase simulée, ou `null` quand le schéma a été honoré. */
export function noteDEcart(phase: PhaseSimulee): string | null {
  // Honnêteté d'outil : le **bot de simulation** ne sait dérouler aucun des quatre formats à
  // rencontres (`_TYPES_DEROULABLES`, DETTE-066) alors que le **moteur** les joue tous depuis
  // E05US027, et il n'honore pas les prélèvements « le reste » / « issue de tour » (ADR-0068 §3).
  // On montre donc l'écart avec ce que le schéma annonçait.
  if (!phase.joue) {
    // ⚠️ **Deux phrases, parce qu'il y a deux causes** (correctif de revue E05US028) : la phrase
    // unique disait « le moteur ne sait pas dérouler ce type », factuellement fausse depuis que les
    // poules et le Big Shoot Off sont jouables — et affichée à l'organisateur la veille du tournoi.
    return MOTEUR_SAIT_JOUER.has(phase.type)
      ? '▲ la simulation ne sait pas encore jouer ce type de phase — le moteur, si : le tournoi réel se déroulera normalement'
      : "▲ le moteur ne sait pas encore dérouler ce type de phase — rien n'a été joué ici"
  }
  if (!phase.ecart) return null
  return `▲ le schéma annonçait ${phase.effectif_projete ?? ''} archers, ${phase.tours_projetes ?? '—'} tours et ${phase.duels_projetes ?? '—'} duels`
}

/** Un compteur de phase simulée : zéro, ou une phase non jouée, s'affiche « — ». */
export function compteurAffiche(joue: boolean, valeur: number): number | '—' {
  return joue && valeur > 0 ? valeur : '—'
}

export const CLASSEMENT_AFFICHE_MAX = 32

export function classementAffiche(classement: readonly LigneClassement[]): {
  lignes: LigneClassement[]
  tronque: boolean
} {
  return {
    lignes: classement.slice(0, CLASSEMENT_AFFICHE_MAX),
    tronque: classement.length > CLASSEMENT_AFFICHE_MAX,
  }
}
