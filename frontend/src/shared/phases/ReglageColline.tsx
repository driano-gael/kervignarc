// La fiche de réglages d'une **colline** (E05US027).
//
// Partagée par les **deux** écrans qui composent des phases — « Composer un format » (un modèle de
// bibliothèque) et « Phases » (les phases d'un tournoi) —, comme `ReglagePoules`,
// `ReglageBigShootOff` et `ReglageSuisse` avant elle.
//
// ⚠️ **Ce composant ne détient AUCUN état** (leçon de la revue d'E06US006, reprise telle quelle) :
// monté sous condition, un état dérivé d'une prop diverge dès que la condition bascule.
//
// **Deux réglages**, et le second est le plus important des deux : la portée de défi est ce qui
// fait un King of the Hill ou un Ladder. C'est pourquoi l'écran **nomme le format** sous le champ
// plutôt que de laisser l'organisateur traduire un nombre.

import type { EtatColline } from './colline'
import {
  MANCHES_MAX_REGLABLES,
  PORTEE_MAX_REGLABLE,
  decrireBorne,
  decrireBorneConnue,
  estValide,
  nommerFormat,
  versReglage,
} from './colline'

/**
 * Rend la fiche de réglages d'une colline. Aucun état : l'unique source est `etat`, détenu par le
 * parent.
 *
 * `effectif` sert **uniquement** à annoncer la borne — `null` quand l'écran ne simule aucun
 * effectif, et l'annonce disparaît alors plutôt que d'énoncer une borne inventée.
 */
export function ReglageColline({
  etat,
  surChangement,
  effectif,
  maximum = null,
}: {
  etat: EtatColline
  surChangement: (etat: EtatColline) => void
  effectif: number | null
  /**
   * La borne **que le serveur a calculée**, quand l'appelant l'a sous la main.
   *
   * ⚠️ Même rôle que chez `ReglageSuisse`, et pour la même raison : sur l'écran des phases, l'état
   * de la phase porte `portee_maximale`, et le recalculer côté client reviendrait à entretenir deux
   * arithmétiques pour une même règle. `null` — le cas de l'atelier, où aucune phase n'existe
   * encore — retombe sur le miroir de `shared/phases/colline.ts`, seul recours possible.
   */
  maximum?: number | null
}) {
  const reglage = versReglage(etat)

  return (
    <fieldset className="deroule__sources">
      <legend>Réglage de la colline</legend>

      <label className="formulaire__libelle">
        Nombre de manches
        <input
          inputMode="numeric"
          placeholder="5"
          value={etat.manches}
          onChange={(e) => surChangement({ ...etat, manches: e.target.value })}
        />
      </label>

      <label className="formulaire__libelle">
        Portée de défi
        <input
          inputMode="numeric"
          placeholder="1"
          value={etat.portee}
          onChange={(e) => surChangement({ ...etat, portee: e.target.value })}
        />
      </label>

      {/* Le nombre seul ne dit rien à l'organisateur : c'est le **nom du format** qu'il reconnaît.
          Le catalogue n'expose qu'un type « colline » parce que le moteur est le même (règle 2),
          mais le club dit « King of the Hill » ou « Ladder ». */}
      {reglage !== undefined && (
        <p className="carte__aide" role="status">
          Portée {reglage.portee_de_defi} — <strong>{nommerFormat(reglage.portee_de_defi)}</strong>.
        </p>
      )}

      <p className="carte__aide">
        Personne n’est éliminé&nbsp;: les archers occupent des positions ordonnées («&nbsp;la
        colline&nbsp;»), et à chaque manche certains s’affrontent —{' '}
        <strong>le gagnant monte, le perdant descend</strong>. À portée 1, on défie son voisin
        immédiat&nbsp;; au-delà, la distance des défis <strong>tourne</strong> d’une manche à
        l’autre. Les archers des extrémités se reposent une manche sur deux&nbsp;: c’est normal, ils
        rejouent la suivante. Le classement final, c’est la colline elle-même.
      </p>

      {/* CA — « la portée maximale que l'effectif autorise, affichée en clair ». Au-delà, ce n'est
          plus un King of the Hill ni un Ladder mais « chacun défie n'importe qui » ; le service
          borne à la lecture plutôt que de refuser d'ouvrir l'écran. */}
      {effectif !== null && reglage !== undefined && (
        <p className="carte__aide" role="status">
          {/* `maximum === null` ⇒ l'effectif vient du **formulaire**, donc le serveur REFUSERA
              au-delà de la borne ; sinon il vient de la phase, et le service **borne à la
              lecture**. `decrireBorne` porte déjà le régime `'refuse'`, cf. `colline.ts`. */}
          {maximum === null
            ? decrireBorne(effectif, reglage.portee_de_defi)
            : decrireBorneConnue(effectif, reglage.portee_de_defi, maximum)}
        </p>
      )}

      {!estValide(etat) && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Indiquez un nombre de manches entre 1 et {MANCHES_MAX_REGLABLES}, et une portée de défi
          entre 1 et {PORTEE_MAX_REGLABLE}.
        </span>
      )}
    </fieldset>
  )
}
