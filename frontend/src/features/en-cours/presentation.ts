// Ce que l'onglet « En cours » **choisit d'afficher** — logique pure, aucun React (E05US031).
//
// Extrait du `.tsx` pour la raison que `features/suisse/presentation.ts` énonce en tête :
// `react-refresh` interdit à un module de rendu d'exporter aussi des fonctions, donc tout ce qui
// vit dans le composant est **intestable**. Les deux fonctions ci-dessous portent chacune un CA de
// l'US — l'atterrissage sur la phase en cours, et le fait qu'un format soit rendable ou non.

import type { TypePhase } from '../../shared/phases/catalogue'

/** La forme d'une phase dont ce module a besoin — volontairement pauvre.
 *
 * Ni sources, ni réglages : ce qui suit ne sert qu'à **ordonner** et à **choisir**. La typer sur
 * `Phase` (`features/phases/api.ts`) interdirait de la tester sans bâtir un agrégat entier. */
export interface PhaseLisible {
  id: number
  ordre: number
  type: TypePhase
  statut: 'a_venir' | 'en_cours' | 'en_pause' | 'terminee'
}

/** La phase sur laquelle l'onglet **atterrit**, ou `null` si le départ n'en porte aucune.
 *
 * Trois règles, dans cet ordre :
 *
 * 1. **la phase démarrée de rang le plus élevé** (`en_cours` ou `en_pause`) ;
 * 2. sinon **la première non terminée** — ce qui va se jouer : entre deux phases, le matin, c'est la
 *    réponse juste et l'en-tête dit « pas encore lancée » ;
 * 3. sinon **la dernière**, parce qu'à 17 h tout est terminé et qu'un écran vide serait pire que
 *    l'ultime phase jouée — c'est justement son résultat que la salle veut voir.
 *
 * ⚠️ **La règle 1 est un correctif de revue (axes C1 et adversarial), et elle vaut d'être comprise.**
 * Une première version se contentait de la règle 2, transposée de `VueTableaux`. La transposition
 * était fausse d'un cran : `VueTableaux` se cale sur `est_termine`, qui est **calculé** à partir des
 * duels, tandis que `StatutPhase` est **déclaratif** — il n'est mû que par les transitions manuelles
 * de l'écran de pilotage, et *aucun* service de tir ne le consulte pour accepter un score. Rien
 * n'oblige donc à clore la phase N avant de démarrer la N+1, et deux phases peuvent être `en_cours`
 * ensemble.
 *
 * Conséquence de la version fausse : une qualification qu'on oublie de passer à « Terminée » — un
 * geste sans effet nulle part ailleurs dans le produit, donc facile à omettre — figeait l'onglet
 * **et l'écran de salle** sur « il n'y a pas de rencontre à suivre » pendant qu'on tirait les duels.
 * Sur le projecteur, `interactif={false}` supprime le fil du déroulé : il n'existait aucun recours,
 * et aucun message d'erreur pour alerter. C'est la première surface du produit **sans opérateur
 * devant elle** dont le contenu dépend d'une case à cocher.
 *
 * ⚠️ **L'ordre vient du serveur** (`ordre`, contigu 1..N par départ, ADR-0076) et n'est pas
 * re-trié ici : deux ordonnancements pour une même séquence divergent tôt ou tard. On se contente
 * de ne pas supposer que la liste arrive triée.
 */
export function phaseAAtterrir(phases: readonly PhaseLisible[]): PhaseLisible | null {
  if (phases.length === 0) return null
  const parOrdre = [...phases].sort((a, b) => a.ordre - b.ordre)
  const demarrees = parOrdre.filter((p) => p.statut === 'en_cours' || p.statut === 'en_pause')
  return (
    demarrees.at(-1) ??
    parOrdre.find((phase) => phase.statut !== 'terminee') ??
    parOrdre.at(-1) ??
    null
  )
}

// ⚠️ **Il n'y a délibérément pas de table « les types que l'onglet sait dessiner » ici.** Une
// première rédaction en portait une, doublant l'aiguillage de `VueEnCours` — et en moins fort :
// une table se désynchronise en silence, alors que le `switch` de l'aiguilleur est gardé par une
// affectation à `never` qui rend **non compilable** l'ajout d'un type de phase sans branche. Deux
// sources pour la même vérité, dont l'une seule est vérifiée, valent moins qu'une seule vérifiée.
