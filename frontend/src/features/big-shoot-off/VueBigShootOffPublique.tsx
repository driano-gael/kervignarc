// La vue **publique** d'un Big Shoot Off (E05US031, ADR-0089).
//
// Un seul composant pour **deux** surfaces, comme `VueTableaux` : l'appli publique et l'écran de
// salle, toutes deux montées par l'aiguilleur `features/en-cours/`.
//
// ⚠️ **« Trois surfaces » jusqu'à la revue** (axe C2) : la formule ajoutait l'écran d'organisation,
// qui ne monte pas cette vue. C'est cette liste qui **justifie** la contrainte « cette vue ne lit
// pas le store » ; l'appuyer sur une surface imaginaire la rend invérifiable.
//
// **L'historique est ici gratuit, comme pour les poules** : une finale se lit en tableau — un
// tireur par ligne, une manche par colonne —, donc toutes les manches jouées sont visibles
// d'emblée. Aucune navigation à bâtir : c'est la forme du format qui la rend inutile.
//
// ⚠️ **La lecture est celle du sort, pas celle du score.** Ce qu'un spectateur vient chercher ici
// est « qui reste en lice » et « qui est sorti à quel rang » — les totaux de manche ne sont qu'un
// moyen de le comprendre. D'où l'ordre des colonnes : le rang d'abord, le détail ensuite.

import { messageDeLecture } from '../../shared/api/etatDeLecture'
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
    return <p className="carte__etat">{messageDeLecture(etat)}</p>
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
        {/* ⚠️ **`paliers` commence APRÈS la première manche** : `paliers_pour` rend « ce qu'il reste
            après chaque manche réellement jouable », donc `8 → 6 → 5` là où la salle attend
            `12 → 8 → 6 → 5`. L'effectif de départ se remet en tête — c'est la forme que la
            docstring du domaine, `shared/phases/bigShootOff.ts` et la fiche de recette emploient
            tous les trois (relevé en revue, axe C1). */}
        {[donnees.format.effectif, ...donnees.format.paliers].join(' → ')} · {donnees.format.volees}{' '}
        volée(s) de {donnees.format.fleches_par_volee} flèches
        {/* ⚠️ **PAS `format.restants`** : c'est le « K dérivé », combien il restera **à la fin**
            (`domain/big_shoot_off.py::restants_pour` = `paliers[-1]`). L'afficher ici annonçait
            « 5 encore en lice » dès la première manche, avec 12 archers sur les cibles, et le
            chiffre ne bougeait pas de la finale — sur l'information même que cette vue existe pour
            donner. Bloquant relevé en revue (axe C1) ; aucun autre axe ne pouvait le voir, le DTO
            étant conforme et cette vue n'ayant alors aucun test de rendu.
            Compté sur `donnees.tireurs` et **jamais** sur `retenus`, qui est filtré par
            « mes archers » — sinon le total dépendrait de qui l'on suit. */}
        {donnees.termine
          ? ' · terminé'
          : ` · ${donnees.tireurs.filter((t) => t.en_lice).length} encore en lice`}
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
            // ⚠️ Le liseré se pose sur la **première cellule**, pas sur le `<tr>` (correctif de
            // revue, axes B et C1) : `padding-left` n'a aucun effet sur une ligne de tableau, et
            // `border-left` n'y rend de façon fiable qu'en `border-collapse`. La recette promet un
            // liseré (scénario 6) ; sur `<tr>` il était au mieux collé au texte.
            <tr key={tireur.archer_id}>
              <td
                className={
                  suivis.includes(tireur.archer_id) ? 'encours__cellule--suivi' : undefined
                }
              >
                {`${tireur.prenom} ${tireur.nom}`.trim()}
              </td>
              <td>{decrireSort(tireur)}</td>
              {jouees.map((manche) => (
                // `scores` ne porte que les manches **entièrement validées** : une case vide dit
                // « pas encore scellée », jamais « zéro ». Un `0` inventé ferait croire à un tir
                // manqué sur un archer dont la feuille est simplement en cours de validation.
                //
                // ⚠️ Indexé par `manche.numero - 1`, **pas** par le rang dans `jouees` (correctif
                // de revue, axe C1). L'alignement des deux tenait aujourd'hui — `jouee` est un
                // préfixe sans trou — mais c'était la coïncidence de deux constructions
                // indépendantes : le jour où une manche serait sautée, les scores glisseraient
                // d'une colonne sans qu'aucun test ne bronche. On exprime la correspondance.
                <td key={manche.numero}>{tireur.scores[manche.numero - 1] ?? '—'}</td>
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
