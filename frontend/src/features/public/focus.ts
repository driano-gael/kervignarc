// La bascule « mes archers / tout » de l'appli publique (E16US004) — logique pure, testée en node.
//
// Le commanditaire suit **plusieurs** archers (P01, confirmé) et veut pouvoir lire tout l'onglet
// public soit en entier, soit centré sur eux : *« il me faut les 2 »* (P03, classement) et *« une
// bascule pour suivre tous les tableaux du tournoi ou uniquement centré sur les archers que l'on
// choisit de suivre »* (P05, tableaux).
//
// **Un seul interrupteur, en tête de l'écran public** (cadrage du 08/08/2026, alternative « un par
// vue » écartée) : le spectateur choisit une fois « je regarde mes archers » et ne le redit pas à
// chaque onglet. D'où ce module — la règle de centrage est la même pour le classement, le palmarès,
// les affectations, les tableaux et le plan de cibles, elle n'a donc qu'un domicile.
//
// ⚠️ **Le mode ne se lit jamais depuis le store à l'intérieur d'une vue partagée.** `VueClassement`,
// `VueTableaux` et `VueAffectations` servent aussi la coquille admin et l'écran de salle : une
// lecture directe du store y ferait fuir le filtre public sur des surfaces qui n'en veulent pas.
// Le mode descend donc en **prop explicite** depuis `AccueilPublic`, comme `filtrable` et
// `interactif` avant lui.

import type { ArcherSuivi } from '../../shared/stores/sessionSuivisStore'

/** Ce que l'écran montre : tout le tournoi, ou seulement les archers suivis. */
export type ModeAffichage = 'tout' | 'suivis'

/** Les archers suivis **sur ce tournoi**.
 *
 * Le store mémorise les suivis de tous les tournois (plusieurs `EN_COURS` en parallèle est une
 * capacité voulue) ; une vue n'en connaît qu'un.
 */
export function suivisDuTournoi(suivis: ArcherSuivi[], tournoiId: number): number[] {
  return suivis.filter((s) => s.tournoiId === tournoiId).map((s) => s.archerId)
}

/** Le mode réellement appliqué.
 *
 * La bascule est mémorisée **globalement** (une préférence de lecture) alors que les suivis sont
 * **par tournoi**. Sans ce garde, ouvrir un tournoi où l'on ne suit personne viderait tous les
 * écrans publics d'un coup — un écran vide qui n'explique pas pourquoi est pire qu'un écran plein.
 */
export function modeEffectif(centrer: boolean, suivisIci: number[]): ModeAffichage {
  return centrer && suivisIci.length > 0 ? 'suivis' : 'tout'
}

/** Restreint une liste de lignes porteuses d'un `archer_id` aux archers suivis.
 *
 * Générique parce que le classement (`LigneClassement`), le palmarès (`LignePalmares`) et les
 * affectations (`RoutageArcher`) portent tous ce champ : trois filtres identiques auraient dérivé.
 *
 * **On filtre, on ne renumérote pas** : le rang affiché reste celui du classement complet, comme le
 * filtre par catégorie livré en E06US001. Un archer 23ᵉ reste 23ᵉ quand on ne regarde que lui.
 */
export function centrerLignes<T extends { archer_id: number }>(
  lignes: T[],
  mode: ModeAffichage,
  suivisIci: number[],
): T[] {
  if (mode === 'tout') return lignes
  const suivis = new Set(suivisIci)
  return lignes.filter((ligne) => suivis.has(ligne.archer_id))
}

/** Restreint un plan de cibles aux **buttes** où tire au moins un archer suivi.
 *
 * On garde la cible **entière**, voisins compris : « où tire mon archer » se cherche des yeux sur
 * une butte, pas sur une place isolée — masquer ses voisins rendrait le plan illisible.
 */
export function centrerCibles<T extends { placements: readonly { archer_id: number }[] }>(
  cibles: T[],
  mode: ModeAffichage,
  suivisIci: number[],
): T[] {
  if (mode === 'tout') return cibles
  const suivis = new Set(suivisIci)
  return cibles.filter((cible) => cible.placements.some((p) => suivis.has(p.archer_id)))
}
