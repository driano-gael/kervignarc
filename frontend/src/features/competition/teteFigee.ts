// Combien de lignes de tête un classement garde **toujours visibles**, selon la surface (E16US009).
//
// Module à part et non une fonction de `VueClassement.tsx` : c'est une **règle de choix**, elle se
// teste sans monter de composant — et `react-refresh` interdit à un fichier de composant d'exporter
// autre chose que des composants.

import type { ModeAffichage } from '../../shared/suivis/focus'
import type { ReglagePages } from '../../shared/ui/pagination'

/** Combien de lignes de tête restent figées, selon la surface (E16US009).
 *
 * Trois cas, et le troisième est le garde-fou : projeté **avec** un réglage de pages → 3 (P07) ;
 * manipulé et non centré sur des suivis → 8 ; sinon **zéro**. Le zéro couvre la liste courte
 * centrée sur ses archers (figer 8 sur 3 lignes n'encadre plus rien) **et** l'écran projeté sans
 * réglage — où figer une tête sans faire tourner le reste amputerait le classement. Pure et nommée
 * plutôt qu'un ternaire dans le JSX : c'est une règle de choix, elle se teste.
 */
export function teteFigee(
  filtrable: boolean,
  mode: ModeAffichage,
  pagination: ReglagePages | undefined,
): number {
  if (!filtrable) return pagination === undefined ? 0 : 3
  return mode === 'tout' ? 8 : 0
}
