// La fiche de réglages du **découpage d'une qualification en tours** (E05US035, ADR-0093).
//
// Partagée par les **deux** écrans qui composent des phases — « Composer un déroulé » (un modèle de
// bibliothèque) et « Phases » (les phases d'un tournoi) —, comme `ReglageSuisse` avant elle.
//
// ⚠️ **Ce composant ne détient AUCUN état** (leçon de la revue d'E06US006, reprise telle quelle) :
// monté sous condition, un état dérivé d'une prop diverge dès que la condition bascule.
//
// **Un seul réglage** : en combien de tours. La longueur en découle, et elle est *annoncée* plutôt
// que saisie — c'est l'arbitrage du cadrage du 20/08/2026, et c'est ce qui garantit des tours
// égaux sans avoir à valider une liste de longueurs.

import type { EtatDecoupage } from './decoupage'
import { TOURS_MAX_REGLABLES, decrireDecoupage, estValide, versDecoupage } from './decoupage'

/**
 * Rend la fiche de découpage d'une qualification. Aucun état : l'unique source est `etat`, détenu
 * par le parent.
 *
 * `nbVolees` sert **uniquement** à annoncer la longueur d'un tour — `null` quand l'écran ne connaît
 * aucun barème (l'atelier compose un format de bibliothèque), et l'annonce se contente alors de
 * dire que la longueur dépendra du tournoi, plutôt que d'inventer un dénominateur.
 */
export function ReglageDecoupage({
  etat,
  surChangement,
  nbVolees,
}: {
  etat: EtatDecoupage
  surChangement: (etat: EtatDecoupage) => void
  nbVolees: number | null
}) {
  const decoupage = versDecoupage(etat)

  return (
    <fieldset className="deroule__sources">
      <legend>Découpage en tours</legend>

      <label className="formulaire__libelle">
        Nombre de tours
        <input
          inputMode="numeric"
          placeholder="1"
          value={etat.tours}
          onChange={(e) => surChangement({ tours: e.target.value })}
        />
      </label>
      <p className="carte__aide">
        Découper la qualification ne change <strong>rien au classement</strong>&nbsp;: elle se
        compte toujours au total des volées. Cela sert uniquement à donner à une{' '}
        <strong>pause programmée</strong> un endroit où tomber — sans découpage, la qualification se
        tire d’un seul bloc et aucune pause ne peut s’y poser.
      </p>

      {/* La longueur obtenue, ou la raison du refus à venir. Le domaine exige des tours **égaux** ;
          la dire ici évite à l'organisateur de la découvrir par un 422 à la soumission. */}
      {decoupage !== undefined && (
        <p className="carte__aide" role="status">
          {decrireDecoupage(nbVolees, decoupage === null ? 1 : decoupage.nb_tours)}
        </p>
      )}

      {!estValide(etat) && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Indiquez un nombre de tours entier, entre 1 et {TOURS_MAX_REGLABLES}.
        </span>
      )}
    </fieldset>
  )
}
