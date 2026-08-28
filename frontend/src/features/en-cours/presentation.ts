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
 * Trois règles : la phase démarrée de rang le plus élevé (`en_cours`/`en_pause`) ; sinon la
 * première non terminée ; sinon la dernière. ⚠️ **La règle 1 est un correctif de revue** :
 * `StatutPhase` est **déclaratif**, mû par les seules transitions manuelles, donc deux phases
 * peuvent être `en_cours` ensemble — une qualification non close figeait l'écran de salle sur «
 * aucune rencontre ». ⚠️ **L'ordre vient du serveur** (`ordre`, ADR-0076), non re-trié ici.
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
