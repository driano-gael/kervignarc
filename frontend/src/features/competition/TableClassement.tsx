// Tableau du classement de qualification (E06US001). Une ligne par archer : rang **de catégorie** et
// rang **scratch** (global), identité, catégorie, cible, total, et le décompte de **10** et de **9**
// qui rend le départage FFTA lisible (à total égal, plus de 10 puis de 9 — `referentiel-ffta` §8.1).
// Il se rafraîchit tout seul à chaque saisie (invalidation via le flux temps réel).
//
// Surface de **lecture** : le classement sert à connaître les positions. Le placement inline reste
// offert à l'admin (colonne « Placer ») ; la saisie des scores, elle, se fait sur l'écran de saisie
// dédié (E04US002) — l'ancien bouton « Marquer » du walking skeleton écrivait un score que le
// classement ne lit plus (il dérive des séries de saisie), il a donc été retiré.
//
// Le club encore inconnu y est signalé (E02US002, ADR-0014) : le classement est la surface qu'on
// regarde toute la journée, c'est là que l'anomalie se remarque ; l'écran d'admin la répare.

import { useState } from 'react'
import type { LigneClassement } from './api'
import { aDesExAequo, estExAequo, totauxExAequo } from './departage'
import { usePlacerArcher } from './hooks'

interface TableClassementProps {
  tournoiId: number
  lignes: LigneClassement[]
  admin: boolean
  /**
   * Combien de lignes de tête restent **toujours visibles** pendant que le reste défile (A16 :
   * *« les x premiers sont toujours affichés, mais le dessous du tableau a un défilé jusqu'à n »*).
   *
   * `0` = pas de séparation, le tableau se comporte comme avant. La valeur est un **paramètre** et
   * non une constante parce que « x » n'a pas la même valeur partout : trois sur un écran de salle
   * (P07 : *« ok pour les 3 premiers toujours visible »*), davantage sur un PC d'organisation où
   * l'on suit le haut d'une catégorie.
   */
  teteFigee?: number
}

export function TableClassement({ tournoiId, lignes, admin, teteFigee = 0 }: TableClassementProps) {
  if (lignes.length === 0) {
    return <p className="carte__etat">Aucun archer inscrit pour l'instant.</p>
  }

  const egalites = totauxExAequo(lignes)
  // Séparation seulement si elle **sert** : figer les 5 premiers d'une liste de 5 ne fait
  // qu'ajouter un cadre autour de rien.
  const separer = teteFigee > 0 && lignes.length > teteFigee
  const tete = separer ? lignes.slice(0, teteFigee) : lignes
  const reste = separer ? lignes.slice(teteFigee) : []

  const corps = (source: LigneClassement[]) => (
    <tbody>
      {source.map((ligne) => (
        <LigneArcher
          key={ligne.archer_id}
          tournoiId={tournoiId}
          ligne={ligne}
          admin={admin}
          exAequo={estExAequo(ligne, egalites)}
        />
      ))}
    </tbody>
  )

  return (
    <div className="classement">
      <table className="table">
        <Colonnes admin={admin} />
        <thead>
          <tr>
            <th scope="col">Rang cat.</th>
            <th scope="col">Scratch</th>
            <th scope="col">Archer</th>
            <th scope="col">Catégorie</th>
            <th scope="col">Cible</th>
            <th scope="col">Total</th>
            <th scope="col" title="Nombre de 10 (départage FFTA)">
              10
            </th>
            <th scope="col" title="Nombre de 9 (départage FFTA)">
              9
            </th>
            {admin && <th scope="col">Placer</th>}
          </tr>
        </thead>
        {corps(tete)}
      </table>

      {/* Le reste, dans son propre cadre défilant. Deux tables et non une seule à lignes
          `position: sticky` : figer des `<tr>` demande de connaître la hauteur de chaque ligne pour
          calculer leur `top`, or une ligne peut grandir (badge « Club inconnu », nom qui passe à la
          ligne) — le calage aurait été juste jusqu'au premier cas réel. `table-layout: fixed` et un
          `<colgroup>` **partagé** (cf. `Colonnes`) garantissent l'alignement des colonnes entre les
          deux tables, sans mesure ni JavaScript. */}
      {separer && (
        <div className="classement__defilement">
          <table className="table">
            <Colonnes admin={admin} />
            {corps(reste)}
          </table>
        </div>
      )}

      {/* **La règle de départage, seulement en cas d'ex æquo** (A16). En permanence, elle explique
          une règle qui ne s'applique pas — et un écran qui explique en continu finit par ne plus
          être lu. Les lignes concernées sont marquées : dire « il y a des ex æquo » sans dire
          lesquels serait une devinette. */}
      {aDesExAequo(egalites) && (
        <p className="classement__departage" role="note">
          Ex æquo signalés : à total égal, le plus grand nombre de <strong>10</strong> départage,
          puis le nombre de <strong>9</strong> (règle FFTA).
        </p>
      )}
    </div>
  )
}

/** Le `<colgroup>` **partagé** par la table de tête et la table défilante — c'est lui qui fait que
 * les colonnes restent alignées entre les deux, sans mesurer quoi que ce soit au rendu. */
function Colonnes({ admin }: { admin: boolean }) {
  return (
    <colgroup>
      <col className="classement__col--rang" />
      <col className="classement__col--rang" />
      <col />
      <col className="classement__col--categorie" />
      <col className="classement__col--court" />
      <col className="classement__col--court" />
      <col className="classement__col--court" />
      <col className="classement__col--court" />
      {admin && <col className="classement__col--action" />}
    </colgroup>
  )
}

function LigneArcher({
  tournoiId,
  ligne,
  admin,
  exAequo,
}: {
  tournoiId: number
  ligne: LigneClassement
  admin: boolean
  exAequo: boolean
}) {
  const [cible, setCible] = useState('')
  const placer = usePlacerArcher(tournoiId)

  const soumettrePlacement = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    const valeur = Number(cible)
    if (!Number.isInteger(valeur) || valeur < 1) return
    placer.mutate({ archerId: ligne.archer_id, cible: valeur }, { onSuccess: () => setCible('') })
  }

  // Nom **et** prénom : depuis E02US002, deux homonymes confirmés (un père et son fils) peuvent
  // coexister — les distinguer à l'écran est le minimum vital.
  const identite = `${ligne.nom} ${ligne.prenom}`

  // Statut forfait (E04US015, ADR-0050) : un abandon est relégué (rang affiché), une DSQ est sortie
  // du classement (rang `null` → « — »). Le badge rend le statut visible ; le score reste affiché
  // (les flèches sont préservées).
  const badgeStatut =
    ligne.statut === 'abandon' ? 'Abandon' : ligne.statut === 'disqualifie' ? 'Disqualifié' : null

  // Deux marquages indépendants, qui peuvent se cumuler sans se contredire : forfait (le score
  // reste, le rang part) et ex æquo (le rang tient à un départage).
  const classes = [
    ligne.statut !== 'en_lice' ? 'table__ligne--forfait' : '',
    exAequo ? 'table__ligne--ex-aequo' : '',
  ]
    .filter((c) => c !== '')
    .join(' ')

  return (
    <tr className={classes === '' ? undefined : classes}>
      <td>{ligne.rang_categorie ?? '—'}</td>
      <td className="table__scratch">{ligne.rang_scratch ?? '—'}</td>
      <td>
        {identite}
        {badgeStatut && (
          <span className="table__badge-forfait" title="Statut de participation">
            {' '}
            {badgeStatut}
          </span>
        )}
        {ligne.club_id === null && (
          <span
            className="table__anomalie"
            title="Renseignez son club pour compléter l'inscription"
          >
            {' '}
            Club inconnu
          </span>
        )}
      </td>
      <td>{ligne.categorie_libelle}</td>
      <td>{ligne.cible ?? '—'}</td>
      <td className="table__total">{ligne.total}</td>
      <td>{ligne.nb_dix}</td>
      <td>{ligne.nb_neuf}</td>
      {admin && (
        <td>
          <form className="ligne-action" onSubmit={soumettrePlacement}>
            <input
              className="ligne-action__champ"
              type="number"
              min={1}
              value={cible}
              onChange={(e) => setCible(e.target.value)}
              aria-label={`Cible de ${identite}`}
            />
            <button type="submit" disabled={placer.isPending || cible === ''}>
              OK
            </button>
          </form>
        </td>
      )}
    </tr>
  )
}
