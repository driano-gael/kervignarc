// La **colline elle-même** (E05US027) — c'est-à-dire le classement.
//
// Sorti du `.tsx` de saisie comme `ClassementSuisse` l'a été en revue d'E05US030, et pour la même
// raison : l'organisateur en a autant besoin que le scoreur, et l'écran des phases lit déjà l'état
// de la phase pour son bouton de plan — il porte donc le même tableau sans un appel de plus.
//
// ⚠️ **Ce tableau n'est pas « un classement provisoire », c'est l'état du jeu.** Chez le suisse, le
// classement se *calcule* des résultats (points, Buchholz) ; ici la colline **est** le classement,
// et c'est tout l'intérêt du format — un spectateur lit à tout instant qui est où, sans attendre la
// fin de la phase.
//
// ⚠️ **Ni rang sportif ni ex æquo**, à la différence du suisse : deux archers n'occupent jamais la
// même position. Il n'y a donc pas de convention « 1224 » à afficher, et aucune égalité ne peut
// retenir une phase avale (ADR-0081).

import type { RangColline } from './api'
import { nomDeLArcher, type MancheLisible } from './presentation'

export function ClassementColline({
  classement,
  manches,
}: {
  classement: readonly RangColline[]
  manches: readonly MancheLisible[]
}) {
  if (classement.length === 0) return null

  const closes = manches.filter((m) => m.close).length

  return (
    <table className="deroule__table">
      <caption>La colline après {closes} manche(s)</caption>
      <thead>
        <tr>
          <th>Position</th>
          <th>Archer</th>
        </tr>
      </thead>
      <tbody>
        {classement.map((ligne) => (
          <tr key={ligne.archer_id}>
            <td>{ligne.position}</td>
            <td>{nomDeLArcher(manches, ligne.archer_id)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
