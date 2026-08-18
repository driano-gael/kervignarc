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
 * La règle est celle de `VueTableaux` — « la première non terminée, sinon la dernière » — et elle
 * n'est pas arbitraire :
 *
 * - **la première non terminée** est ce qui se joue ou ce qui va se jouer. C'est la réponse juste
 *   pendant toute la journée ;
 * - **sinon la dernière**, parce qu'à 17 h tout est terminé et qu'un écran vide serait pire que
 *   l'ultime phase jouée — c'est justement son résultat que la salle veut voir.
 *
 * ⚠️ **L'ordre vient du serveur** (`ordre`, contigu 1..N par départ, ADR-0076) et n'est pas
 * re-trié ici : deux ordonnancements pour une même séquence divergent tôt ou tard. On se contente
 * de ne pas supposer que la liste arrive triée.
 */
export function phaseAAtterrir(phases: readonly PhaseLisible[]): PhaseLisible | null {
  if (phases.length === 0) return null
  const parOrdre = [...phases].sort((a, b) => a.ordre - b.ordre)
  return parOrdre.find((phase) => phase.statut !== 'terminee') ?? parOrdre.at(-1) ?? null
}

// ⚠️ **Il n'y a délibérément pas de table « les types que l'onglet sait dessiner » ici.** Une
// première rédaction en portait une, doublant l'aiguillage de `VueEnCours` — et en moins fort :
// une table se désynchronise en silence, alors que le `switch` de l'aiguilleur est gardé par une
// affectation à `never` qui rend **non compilable** l'ajout d'un type de phase sans branche. Deux
// sources pour la même vérité, dont l'une seule est vérifiée, valent moins qu'une seule vérifiée.
