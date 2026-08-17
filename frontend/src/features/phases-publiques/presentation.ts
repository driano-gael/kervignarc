// Règles de lecture de l'index des phases publiques (E05US031) — logique pure, testée en node.
//
// Deux décisions vivent ici plutôt que dans le JSX, et ce n'est pas une préférence de style : sur
// l'écran de salle, **personne ne peut corriger un mauvais choix**. Une phase mal élue s'y affiche
// huit heures durant. C'est exactement ce qu'ADR-0064 §2 tire de son propre échec (*la logique
// d'arbitrage vivait dans le JSX, donc hors de toute épreuve*).

import type { StatutPhase } from '../phases/api'
import type { PhasePublique } from './api'

/** Quelle vue rend ce type de phase (ADR-0089 §1).
 *
 * `ailleurs` n'est pas un défaut : une qualification **a** sa lecture publique, c'est l'onglet
 * « Classement » ; un échauffement ne produit ni point ni classement **par définition** (§10.1),
 * donc il n'y a rien à montrer. Les nommer ainsi permet de le **dire** au lieu de laisser un écran
 * vide — et un écran de salle n'a personne devant lui pour comprendre ce qui manque (ADR-0064).
 */
export type RenduPhase = 'tableau' | 'poules' | 'suisse' | 'big_shoot_off' | 'ailleurs'

export function renduDe(type: string): RenduPhase {
  // ⚠️ **Exhaustif par construction, pas par `Record`** : `type` est une chaîne serveur, qui peut
  // valoir un type que ce bundle ignore (l'appli publique reste ouverte des heures sur un
  // téléphone, un backend peut être plus récent). Le repli `ailleurs` est donc le seul comportement
  // honnête — il affiche une ligne au lieu d'un blanc. C'est la même raison que le repli de
  // `nommerType`, et la même que celle pour laquelle il n'y en a **pas** dans `LIBELLE_TYPE`.
  switch (type) {
    case 'elimination_directe':
    case 'placement':
      return 'tableau'
    case 'poules':
      return 'poules'
    case 'suisse':
      return 'suisse'
    case 'big_shoot_off':
      return 'big_shoot_off'
    default:
      return 'ailleurs'
  }
}

export const LIBELLE_STATUT_PHASE: Record<StatutPhase, string> = {
  a_venir: 'à venir',
  en_cours: 'en cours',
  en_pause: 'en pause',
  terminee: 'terminée',
}

/** La phase à montrer quand personne ne choisit — l'écran de salle, et l'ouverture de l'onglet.
 *
 * L'ordre de préférence dit une intention simple : **ce qui se joue maintenant**, sinon ce qui vient
 * de se jouer.
 *
 *  1. la première phase **en cours** (plusieurs peuvent l'être : deux blocs d'un même créneau) ;
 *  2. sinon la première **en pause** — arrêtée, mais c'est encore d'elle qu'on parle dans la salle ;
 *  3. sinon la **dernière terminée** : à 17 h, c'est son classement qu'on vient lire, pas celui du
 *     matin. C'est la même règle que `VueTableaux` applique déjà aux arbres ;
 *  4. sinon la première **à venir** — le matin, avant que rien ne commence.
 */
export function phaseAMontrer(phases: PhasePublique[]): PhasePublique | null {
  const ordonnees = [...phases].sort((a, b) => a.ordre - b.ordre)
  return (
    ordonnees.find((p) => p.statut === 'en_cours') ??
    ordonnees.find((p) => p.statut === 'en_pause') ??
    [...ordonnees].reverse().find((p) => p.statut === 'terminee') ??
    ordonnees.find((p) => p.statut === 'a_venir') ??
    null
  )
}

/** La phase effectivement affichée : celle qu'on a choisie si elle existe encore, sinon la règle
 * ci-dessus.
 *
 * ⚠️ Le repli n'est pas décoratif : la liste des phases se rafraîchit toute seule, et une phase
 * choisie peut **disparaître** (l'organisateur la retire du déroulé pendant que le spectateur la
 * regarde). Sans ce repli, l'onglet se vidait sans un mot.
 */
export function phaseAffichee(
  phases: PhasePublique[],
  choisie: number | null,
): PhasePublique | null {
  if (choisie !== null) {
    const trouvee = phases.find((p) => p.id === choisie)
    if (trouvee !== undefined) return trouvee
  }
  return phaseAMontrer(phases)
}
