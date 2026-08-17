// Accès HTTP de l'**index des phases publiques** (E05US031, ADR-0089 §4).
//
// **Pourquoi une lecture propre alors que `features/phases` interroge déjà cette route.** Trois
// raisons, dont la première suffirait :
//
//  1. **La portée.** `features/phases/api.ts` appelle avec la portée par défaut (`'admin'`), donc
//     joint le jeton d'administration s'il en traîne un. Cette lecture-ci est **anonyme** par
//     nature : la déclarer `'aucune'` dit ce qu'elle est, au lieu de marcher par accident parce que
//     le serveur n'exige rien.
//  2. **Le contrat.** `PhaseReponse` sert **tout** le réglage — `sources`, `poules`, `suisse`,
//     `big_shoot_off`, `profondeur`. L'appli publique n'a besoin que de l'identité, du rang, du type
//     et du statut. Nommer un type **plus étroit** est ce qui empêche un écran public d'afficher un
//     jour un réglage d'atelier « puisqu'il est là » (règle 6, dans l'esprit : le client public ne
//     déclare que ce qu'il consomme).
//  3. **Le cache.** La clé de `features/phases` est invalidée par les quatre mutations d'atelier ;
//     l'appli publique n'a rien à voir avec ces invalidations et ne doit pas les subir.
//
// ⚠️ **Ce que ce module ne corrige pas** : la route sert bel et bien les réglages complets à qui
// l'interroge, et elle est publique depuis sa création. Ce n'est pas introduit ici — mais cette US en
// fait un consommateur de plus, donc un motif de moins pour la restreindre un jour. Signalé dans
// ADR-0089 § Conséquences ; la restreindre est une US, pas un correctif de bord.

import { fetchJson } from '../../shared/api/client'
import type { StatutPhase } from '../phases/api'

/** Une phase du créneau, **vue du public** : de quoi la nommer, l'ordonner et la router.
 *
 * `type` est une chaîne de `TypePhase` — le libellé se prend dans `shared/phases/catalogue.ts`
 * (`nommerType`), qui est son domicile unique (règle 3).
 */
export interface PhasePublique {
  id: number
  ordre: number
  type: string
  statut: StatutPhase
}

export function getPhasesPubliques(departId: number): Promise<PhasePublique[]> {
  return fetchJson<PhasePublique[]>(`/api/v1/departs/${departId}/phases`, undefined, 'aucune')
}
