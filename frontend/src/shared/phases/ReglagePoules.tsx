// La fiche de réglages d'une phase de **poules** (E05US023, ADR-0083).
//
// Partagée par les **deux** écrans qui composent des phases — « Composer un déroulé » (un modèle de
// bibliothèque) et « Phases » (les phases d'un tournoi) —, comme `ChoixProfondeur` avant elle. Les
// deux sites existent aujourd'hui : ce n'est pas un pattern posé par anticipation.
//
// ⚠️ **Ce composant ne détient AUCUN état**, et c'est la leçon de la revue d'E06US006 reprise telle
// quelle : monté sous condition (`{estPoules && <ReglagePoules/>}`), un état dérivé d'une prop
// diverge dès que la condition bascule — retyper la phase le démonte, y revenir le remonte
// réinitialisé, pendant que le parent, lui, garde l'ancienne valeur. L'écran afficherait alors une
// taille de poule que le formulaire n'enverrait pas.
//
// **Trois réglages, et un quatrième qui n'en est pas un** (ADR-0083 §5) : la taille visée, le
// barème, et *ce que la poule produit*. Ce dernier n'est pas un champ de plus en base — c'est la
// présence ou l'absence de `nb_qualifies` — mais l'écran doit le **poser en question** plutôt que
// de laisser l'organisateur deviner qu'un champ vide veut dire « la poule classe ».

import type { EtatPoules } from './poules'
import { decrireRepartition, estValide, repartition } from './poules'

// Ce que chaque régime d'ex æquo implique, énoncé sous le choix (exigence `P-4` : chiffrer au
// moment du choix, pas le découvrir à 10 h).
const AIDE_PRODUIT: Record<EtatPoules['produit'], string> = {
  classement:
    'La poule classe ses membres, et ce classement est le livrable : tout ex æquo que les cinq ' +
    'critères ne séparent pas devra être départagé au barrage.',
  qualifies:
    'Seul le franchissement de la barre compte : un barrage n’est demandé que si l’égalité tombe ' +
    'pile dessus. Deux archers à égalité aux rangs 3-4 d’une poule qui en qualifie 2 restent à ' +
    'égalité.',
}

/**
 * Rend la fiche de réglages de poules. Aucun état : l'unique source est `etat`, détenu par le
 * parent.
 *
 * `effectif` sert **uniquement** à l'aperçu de répartition — `null` quand l'écran ne simule aucun
 * effectif, et l'aperçu disparaît alors plutôt que d'annoncer un nombre de poules inventé.
 */
export function ReglagePoules({
  etat,
  surChangement,
  effectif,
}: {
  etat: EtatPoules
  surChangement: (etat: EtatPoules) => void
  effectif: number | null
}) {
  const changer = (champ: Partial<EtatPoules>) => surChangement({ ...etat, ...champ })
  const tailles = effectif === null ? [] : repartition(effectif, Number(etat.taille))

  return (
    <fieldset className="deroule__sources">
      <legend>Réglage des poules</legend>

      <label className="formulaire__libelle">
        Taille de poule
        <input
          inputMode="numeric"
          value={etat.taille}
          onChange={(e) => changer({ taille: e.target.value })}
        />
      </label>
      {/* CA — « la répartition obtenue est montrée avant d'être validée ». C'est ce qui rend
          l'arrondi lisible plutôt que surprenant, et inoffensif le cas extrême (7 archers en
          poules de 4 → une poule de 7, que l'organisateur voit et corrige s'il n'en veut pas). */}
      {tailles.length > 0 && (
        <p className="carte__aide" role="status">
          À {effectif} archers : {decrireRepartition(tailles)}.
        </p>
      )}

      <label className="formulaire__libelle">
        Ce que la poule produit
        <select
          value={etat.produit}
          onChange={(e) => changer({ produit: e.target.value as EtatPoules['produit'] })}
        >
          <option value="classement">Un classement</option>
          <option value="qualifies">Un nombre de qualifiés</option>
        </select>
      </label>
      {etat.produit === 'qualifies' && (
        <label className="formulaire__libelle">
          Qualifiés par poule
          <input
            inputMode="numeric"
            value={etat.qualifies}
            onChange={(e) => changer({ qualifies: e.target.value })}
          />
        </label>
      )}
      <p className="carte__aide">{AIDE_PRODUIT[etat.produit]}</p>

      <div className="reglage-poules__bareme">
        <label className="formulaire__libelle">
          Victoire
          <input
            inputMode="numeric"
            value={etat.victoire}
            onChange={(e) => changer({ victoire: e.target.value })}
          />
        </label>
        <label className="formulaire__libelle">
          Nul
          <input
            inputMode="numeric"
            value={etat.nul}
            onChange={(e) => changer({ nul: e.target.value })}
          />
        </label>
        <label className="formulaire__libelle">
          Défaite
          <input
            inputMode="numeric"
            value={etat.defaite}
            onChange={(e) => changer({ defaite: e.target.value })}
          />
        </label>
      </div>
      <p className="carte__aide">
        Points de match d’une rencontre. Le défaut FFTA du club est 3 / 1 / 0 : il écarte davantage
        un vainqueur d’un archer qui accumule les nuls.
      </p>

      {/* Le départage inter-poules (ADR-0083 §6). Il est **optionnel et auto-régulé** : sans lui,
          une phase avale qui prend le bloc entier des vainqueurs passe, et une qui le coupe est
          refusée **et annoncée**. L'organisateur n'a donc à l'activer que quand l'outil le lui dit —
          d'où l'aide, qui dit quand c'est utile plutôt que d'inviter à cocher par précaution. */}
      <label className="formulaire__libelle formulaire__libelle--choix">
        <input
          type="checkbox"
          checked={etat.departage}
          onChange={(e) => changer({ departage: e.target.checked })}
        />
        Départager les archers de même rang de poule
      </label>
      <p className="carte__aide">
        Sans départage, les vainqueurs de poule sont à égalité entre eux : une phase suivante peut
        les prendre <em>tous</em>, mais pas en choisir une partie. Cochez si vous devez prélever à
        l’intérieur d’un rang — l’outil vous le dira le cas échéant.
      </p>

      {!estValide(etat) && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Complétez la taille de poule (au moins 2) et le barème
          {etat.produit === 'qualifies' ? ', ainsi que le nombre de qualifiés' : ''}.
        </span>
      )}
    </fieldset>
  )
}
