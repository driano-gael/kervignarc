// La vue **publique** d'un Big Shoot Off (E05US031, ADR-0089).
//
// Un seul composant pour trois surfaces, comme `VueTableaux` : l'appli publique, l'écran de salle
// et l'écran d'organisation.
//
// **L'historique est ici gratuit, comme pour les poules** : une finale se lit en tableau — un
// tireur par ligne, une manche par colonne —, donc toutes les manches jouées sont visibles
// d'emblée. Aucune navigation à bâtir : c'est la forme du format qui la rend inutile.
//
// ⚠️ **La lecture est celle du sort, pas celle du score.** Ce qu'un spectateur vient chercher ici
// est « qui reste en lice » et « qui est sorti à quel rang » — les totaux de manche ne sont qu'un
// moyen de le comprendre. D'où l'ordre des colonnes : le rang d'abord, le détail ensuite.

import { type ModeAffichage } from '../../shared/suivis/focus'
import type { TireurPublic } from './api'
import { useEtatBigShootOff } from './hooks'

export function VueBigShootOffPublique({
  tournoiId,
  phaseId,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  phaseId: number
  mode?: ModeAffichage
  suivis?: number[]
}) {
  const etat = useEtatBigShootOff(tournoiId, phaseId)
  const donnees = etat.data

  if (donnees === undefined) {
    return (
      <p className="carte__etat">
        {etat.isError ? 'Connexion momentanément perdue — mise à jour au retour.' : 'Chargement…'}
      </p>
    )
  }
  if (donnees.tireurs.length === 0) {
    return <p className="carte__etat">Les finalistes ne sont pas encore connus.</p>
  }

  const retenus =
    mode === 'suivis'
      ? donnees.tireurs.filter((t) => suivis.includes(t.archer_id))
      : donnees.tireurs
  if (retenus.length === 0) {
    // ⚠️ **Aucun de vos archers ici ≠ aucun finaliste** (ADR-0079). Le cas est même le plus
    // fréquent des trois formats : une finale n'engage qu'une poignée d'archers.
    return (
      <p className="carte__etat">
        Aucun des archers que vous suivez n’est en finale. Passez à « Tout le tournoi » pour la
        suivre quand même.
      </p>
    )
  }

  // Les manches **déjà jouées** portent les colonnes : en afficher de vides ferait lire une finale
  // plus longue qu'elle ne le sera, le réglage pouvant dépasser l'effectif (`manches_ignorees`).
  const jouees = donnees.manches.filter((manche) => manche.jouee)

  return (
    <div className="encours">
      <p className="encours__entete">
        {donnees.format.paliers.join(' → ')} · {donnees.format.volees} volée(s) de{' '}
        {donnees.format.fleches_par_volee} flèches
        {donnees.termine ? ' · terminé' : ` · ${donnees.format.restants} encore en lice`}
      </p>

      {/* Une égalité **suspend** la phase : sans ce mot, la salle voit une manche saisie et validée
          qui n'élimine personne, et rien n'explique pourquoi la suivante ne part pas. */}
      {donnees.barrage !== null && (
        <p className="carte__etat">
          Barrage en cours entre {donnees.barrage.noms.join(', ')} pour{' '}
          {donnees.barrage.places === 1 ? 'une place' : `${donnees.barrage.places} places`}.
        </p>
      )}

      <table className="deroule__table">
        <caption>Finalistes</caption>
        <thead>
          <tr>
            <th>Archer</th>
            <th>Sort</th>
            {jouees.map((manche) => (
              <th key={manche.numero}>M{manche.numero}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {retenus.map((tireur) => (
            <tr
              key={tireur.archer_id}
              className={suivis.includes(tireur.archer_id) ? 'encours__ligne--suivi' : undefined}
            >
              <td>{`${tireur.prenom} ${tireur.nom}`.trim()}</td>
              <td>{decrireSort(tireur)}</td>
              {jouees.map((manche, index) => (
                // `scores` ne porte que les manches **entièrement validées** : une case vide dit
                // « pas encore scellée », jamais « zéro ». Un `0` inventé ferait croire à un tir
                // manqué sur un archer dont la feuille est simplement en cours de validation.
                <td key={manche.numero}>{tireur.scores[index] ?? '—'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Le sort d'un finaliste en toutes lettres.
 *
 * `rang` est `null` tant que l'archer est en lice — un rang annoncé avant la sortie serait un faux
 * départ, et c'est le serveur qui tient cette règle (cf. `TireurAffiche`). L'écran se contente donc
 * de la rendre lisible. */
function decrireSort(tireur: TireurPublic): string {
  if (tireur.en_lice) return 'en lice'
  return tireur.rang === null ? 'sorti' : `${tireur.rang}ᵉ`
}
