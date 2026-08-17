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

/** Le statut en toutes lettres, avec un **repli qui reste lisible**.
 *
 * Même raison que le repli `ailleurs` de `renduDe`, dix lignes plus haut : `statut` vient du
 * serveur et l'appli publique reste ouverte des heures sur un téléphone. Indexer le `Record`
 * directement rendait une chaîne **vide** pour un statut qu'un backend plus récent nommerait —
 * « Poules · » dans l'en-tête et dans chaque option du sélecteur. Le raisonnement était juste à
 * dix lignes de là, mais appliqué à une seule des deux valeurs serveur.
 *
 * ⚠️ **Le paramètre est une `string`, et c'est ce qui rend le repli réel** (correction de la 2ᵉ
 * passe de revue). Typé `StatutPhase`, il annonçait une protection que le type interdisait
 * d'atteindre : `LIBELLE_STATUT_PHASE` est un `Record` **total** sur cette union, donc `?? statut`
 * était statiquement mort — alors que le danger, lui, est bien réel et vient d'ailleurs. TypeScript
 * ne valide rien à l'exécution : un JSON qui porte `"annulee"` traverse le type sans être vu.
 * `renduDe` prend une `string` pour exactement cette raison. */
export function libelleStatut(statut: string): string {
  // ⚠️ Le repli ne rend **pas** la valeur brute : ce serait montrer un code d'enum au spectateur —
  // « Poules · statut_2027 » —, exactement ce que `libelleConflit` s'interdit soixante lignes plus
  // loin dans le même module. Deux doctrines opposées sur la même classe de valeur, relevé par
  // l'axe adversarial. On dit qu'on ne sait pas, en français.
  return LIBELLE_STATUT_PHASE[statut as StatutPhase] ?? 'statut inconnu'
}

/** La phase à montrer quand personne ne choisit — l'écran de salle, et l'ouverture de l'onglet.
 *
 * L'ordre de préférence dit une intention simple : **ce qui se joue maintenant**, sinon ce qui vient.
 *
 *  1. la première phase **en cours** (plusieurs peuvent l'être : deux blocs d'un même créneau) ;
 *  2. sinon la première **en pause** — arrêtée, mais c'est encore d'elle qu'on parle dans la salle ;
 *  3. sinon la première **à venir** ;
 *  4. sinon la **dernière** de la liste — à 17 h, tout est terminé et c'est son classement qu'on
 *     vient lire, pas celui du matin.
 *
 * ⚠️ **« À venir » passe AVANT « dernière terminée », et l'inverse était une régression.** Le
 * backend a tranché ce même arbitrage deux fois — `application/portee.py::la_plus_courante` et
 * `ServicePalmares._resultat`, ce dernier en correctif de revue — avec le motif qui vaut ici mot
 * pour mot : *démarrer une phase est un geste **manuel** de l'organisateur ; faire dépendre un
 * écran public de sa discipline le laisserait muet tout l'après-midi s'il l'oublie*. Avec la
 * priorité inverse, un créneau « qualification terminée + élimination directe pas encore démarrée »
 * affichait la qualification pendant que les duels se tiraient.
 *
 * ⚠️ **Seules les phases qui ont une vue sont candidates.** Les transitions de statut ne sont pas
 * chaînées (`demarrer`/`terminer` ne touchent qu'une phase) : un organisateur qui lance les poules
 * sans « terminer » la qualification laissait l'écran projeté sur « les résultats de la
 * qualification se lisent dans l'onglet Classement » — vrai, mais ce n'est pas ce qui se tire.
 *
 * ⚠️ **La PREMIÈRE démarrée, pas la dernière — arbitrage tranché sur pièce en revue.** L'axe
 * adversarial a proposé `demarrees[-1]` en s'appuyant sur `portee.py::la_plus_avancee`, au motif
 * qu'un organisateur peut lancer une phase sans « terminer » la précédente, laissant deux `en_cours`
 * dont la plus ancienne est figée. Le risque est réel, mais la référence ne s'applique pas :
 * `la_plus_avancee` opère sur les phases **qui admettent un archer donné**, où l'ordre est
 * topologique de *son* parcours, et sa propre docstring prévient — « ne pas confondre avec
 * `la_plus_courante`, qui répond à une autre question : *que se tire-t-il dans ce créneau ?*, **pour
 * un affichage** ». C'est mot pour mot la question posée ici. On suit donc `la_plus_courante`
 * (`demarrees[0]`, puis `a_venir[0]`, puis la dernière). Dévier rouvrirait la divergence front ↔
 * back que cette correction est justement venue fermer.
 *
 * ⚠️ **Le filtre s'applique DANS chaque palier, jamais avant.** C'est une correction de correction,
 * relevée à la seconde passe de revue : filtrer d'abord faisait gagner une phase `a_venir` **avec**
 * vue contre une phase `en_cours` **sans** vue, ce qui retourne la priorité n° 1 que cette même
 * docstring énonce. Le déroulé qui le déclenche est celui de tous les matins — la qualification est
 * toujours `ordre = 1`, et l'élimination directe est composée d'avance : l'onglet se serait ouvert
 * sur l'ED, à afficher « l'arbre n'est pas encore monté », pendant que la qualification se tirait.
 * Le statut décide d'abord ; la vue ne départage qu'à statut égal.
 */
export function phaseAMontrer(phases: PhasePublique[]): PhasePublique | null {
  const ordonnees = [...phases].sort((a, b) => a.ordre - b.ordre)
  const avecVue = ordonnees.filter((p) => renduDe(p.type) !== 'ailleurs')
  // À statut égal, on préfère une phase qu'on sait afficher ; sinon on montre quand même celle qui
  // se joue — mieux vaut la nommer que ne rien dire.
  const choisir = (statut: PhasePublique['statut']) =>
    avecVue.find((p) => p.statut === statut) ?? ordonnees.find((p) => p.statut === statut)
  return (
    choisir('en_cours') ??
    choisir('en_pause') ??
    choisir('a_venir') ??
    avecVue.at(-1) ??
    ordonnees.at(-1) ??
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
