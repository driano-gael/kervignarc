// La fiche de réglages d'un **Big Shoot Off** (E05US028).
//
// Partagée par les **deux** écrans qui composent des phases — « Composer un format » (un modèle de
// bibliothèque) et « Phases » (les phases d'un tournoi) —, comme `ReglagePoules` et
// `ChoixProfondeur` avant elle.
//
// ⚠️ **Ce composant ne détient AUCUN état**, et c'est la leçon de la revue d'E06US006 reprise telle
// quelle : monté sous condition, un état dérivé d'une prop diverge dès que la condition bascule —
// retyper la phase le démonte, y revenir le remonte réinitialisé, pendant que le parent garde
// l'ancienne valeur. L'écran afficherait alors une liste que le formulaire n'enverrait pas.
//
// **Un seul réglage porte la règle** : le nombre de sortants, manche par manche. Le reste est le
// format du tir (volées, flèches) et deux options. ⚠️ **Il n'y a pas de champ « restants »** : le
// nombre d'archers conservés se **déduit** de ce que la liste n'élimine pas. C'est le cœur de
// l'élargissement du 14/08/2026 — deux champs pour la même information pouvaient se contredire.

import type { EtatBigShootOff } from './bigShootOff'
import { decrireProjection, estValide, lireSortants } from './bigShootOff'

/**
 * Rend la fiche de réglages d'un Big Shoot Off. Aucun état : l'unique source est `etat`, détenu par
 * le parent.
 *
 * `effectif` sert **uniquement** à la projection — `null` quand l'écran ne simule aucun effectif, et
 * la projection disparaît alors plutôt que d'annoncer des paliers inventés.
 */
export function ReglageBigShootOff({
  etat,
  surChangement,
  effectif,
}: {
  etat: EtatBigShootOff
  surChangement: (etat: EtatBigShootOff) => void
  effectif: number | null
}) {
  const changer = (champ: Partial<EtatBigShootOff>) => surChangement({ ...etat, ...champ })
  const sortants = lireSortants(etat.sortants)

  return (
    <fieldset className="deroule__sources">
      <legend>Réglage du Big Shoot Off</legend>

      <label className="formulaire__libelle">
        Sortants par manche
        <input
          inputMode="numeric"
          placeholder="4, 2, 1"
          value={etat.sortants}
          onChange={(e) => changer({ sortants: e.target.value })}
        />
      </label>
      <p className="carte__aide">
        Une case par manche&nbsp;: <strong>4, 2, 1</strong> veut dire «&nbsp;quatre sortent au 1
        <sup>er</sup> tour, deux au 2<sup>e</sup>, un au 3<sup>e</sup>&nbsp;». Rien n’impose que la
        liste décroisse ni qu’elle soit régulière. Le nombre d’archers conservés s’en déduit&nbsp;:
        il n’y a pas à le régler.
      </p>

      {/* CA — « la projection est montrée avant d'être validée », patron `ReglagePoules`. C'est la
          contrepartie honnête de « on joue tant que la manche est possible » : le moteur ne refuse
          jamais une liste, il l'écourte — et l'organisateur doit le voir **ici**, pas en salle. */}
      {effectif !== null && sortants !== undefined && (
        <p className="carte__aide" role="status">
          À {effectif} archers&nbsp;: {decrireProjection(effectif, sortants)}
        </p>
      )}

      <div className="reglage-poules__bareme">
        <label className="formulaire__libelle">
          Volées par manche
          <input
            inputMode="numeric"
            value={etat.volees}
            onChange={(e) => changer({ volees: e.target.value })}
          />
        </label>
        <label className="formulaire__libelle">
          Flèches par volée
          <input
            inputMode="numeric"
            value={etat.fleches}
            onChange={(e) => changer({ fleches: e.target.value })}
          />
        </label>
      </div>
      <p className="carte__aide">
        Ce que chaque finaliste tire à chaque manche. Le défaut du club est une volée de 3 flèches.
      </p>

      <label className="formulaire__libelle formulaire__libelle--choix">
        <input
          type="checkbox"
          checked={etat.cumul}
          onChange={(e) => changer({ cumul: e.target.checked })}
        />
        Cumuler les scores entre les manches
      </label>
      <p className="carte__aide">
        Sans cumul (le défaut), on compare le score <em>du tour</em>&nbsp;: un mauvais début ne
        condamne personne, et l’enjeu tient jusqu’à la dernière flèche. Au cumul, un premier tour
        raté pèse jusqu’au bout.
      </p>

      {/* Le départage des sortants (arbitrage du 14/08/2026). Optionnel, et l'aide dit *quand* il
          sert plutôt que d'inviter à cocher par précaution : un barrage immobilise le pas de tir et
          le juge, et celui-ci ne change rien à qui continue. */}
      <label className="formulaire__libelle formulaire__libelle--choix">
        <input
          type="checkbox"
          checked={etat.departageSortants}
          onChange={(e) => changer({ departageSortants: e.target.checked })}
        />
        Départager au barrage les éliminés à égalité
      </label>
      <p className="carte__aide">
        Sans départage, deux archers sortis à la même manche avec le même score{' '}
        <strong>partagent</strong> leur rang. Leur égalité ne change rien à qui continue&nbsp;: elle
        ne décide que d’un numéro. Cochez si le palmarès doit être sans ex æquo — au prix d’un
        barrage de plus, qui immobilise la ligne.
      </p>

      {!estValide(etat) && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Indiquez combien d’archers sortent à chaque manche (au moins 1 par case, séparées par des
          virgules), ainsi que le nombre de volées et de flèches.
        </span>
      )}
    </fieldset>
  )
}
