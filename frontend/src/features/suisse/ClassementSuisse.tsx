// Le classement **provisoire** d'un système suisse (E05US030).
//
// Sorti de `SaisieSuisse.tsx` en revue : le CA le veut « côté organisateur **et** scoreur », et
// seul le scoreur l'avait ; l'écran des phases lit déjà l'état de la phase, il porte donc le même
// tableau sans un appel de plus. C'est la seule lecture d'avancement d'un format sans arbre —
// personne n'est éliminé, donc rien dans la liste des rondes ne dit qui mène — et elle **explique**
// les appariements de la ronde suivante.

import type { RangSuisse } from './api'
import { decrirePoints, nomDeLArcher, type RondeLisible } from './presentation'

export function ClassementSuisse({
  classement,
  rondes,
}: {
  classement: readonly RangSuisse[]
  rondes: readonly RondeLisible[]
}) {
  if (classement.length === 0) return null

  return (
    <table className="deroule__table">
      <caption>Classement après {rondes.filter((r) => r.close).length} ronde(s)</caption>
      <thead>
        <tr>
          <th>Rang</th>
          <th>Archer</th>
          <th>Points</th>
          <th>Buchholz</th>
        </tr>
      </thead>
      <tbody>
        {classement.map((ligne) => (
          <tr key={ligne.archer_id}>
            <td>
              {ligne.rang}
              {ligne.ex_aequo ? ' =' : ''}
            </td>
            <td>{nomDeLArcher(rondes, ligne.archer_id)}</td>
            {/* Les deux colonnes passent par `decrirePoints` : le Buchholz est une **somme** de ces
                mêmes points, donc il est dans la même unité doublée. */}
            <td>{decrirePoints(ligne.points)}</td>
            <td>{decrirePoints(ligne.buchholz)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
