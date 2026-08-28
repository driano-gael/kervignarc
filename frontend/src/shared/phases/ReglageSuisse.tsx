// La fiche de réglages d'un **système suisse** (E05US030).
//
// Partagée par les **deux** écrans qui composent des phases — « Composer un format » et « Phases »
// —, comme `ReglagePoules` et `ReglageBigShootOff` avant elle. ⚠️ **Ce composant ne détient AUCUN
// état** (leçon de la revue d'E06US006) : monté sous condition, un état dérivé d'une prop diverge
// dès que la condition bascule. **Un seul réglage**, le nombre de rondes — tout le reste est
// dérivé.

import type { EtatSuisse } from './suisse'
import {
  RONDES_MAX_REGLABLES,
  decrireBorne,
  decrireBorneConnue,
  estValide,
  versReglage,
} from './suisse'

/**
 * Rend la fiche de réglages d'un système suisse. Aucun état : l'unique source est `etat`, détenu
 * par le parent.
 *
 * `effectif` sert **uniquement** à annoncer la borne — `null` quand l'écran ne simule aucun
 * effectif, et l'annonce disparaît alors plutôt que d'énoncer une borne inventée.
 */
export function ReglageSuisse({
  etat,
  surChangement,
  effectif,
  maximum = null,
}: {
  etat: EtatSuisse
  surChangement: (etat: EtatSuisse) => void
  effectif: number | null
  /**
   * La borne **que le serveur a calculée**, quand l'appelant l'a sous la main.
   *
   * ⚠️ Ce paramètre existe pour ne pas rejouer une règle dont l'autorité est ailleurs : sur l'écran
   * des phases, l'état porte `rondes_maximales`, et le recalculer entretiendrait deux arithmétiques
   * pour une même règle. `null` — le cas de l'atelier — retombe sur le miroir de `suisse.ts`.
   */
  maximum?: number | null
}) {
  const reglage = versReglage(etat)

  return (
    <fieldset className="deroule__sources">
      <legend>Réglage du système suisse</legend>

      <label className="formulaire__libelle">
        Nombre de rondes
        <input
          inputMode="numeric"
          placeholder="5"
          value={etat.rondes}
          onChange={(e) => surChangement({ rondes: e.target.value })}
        />
      </label>
      <p className="carte__aide">
        Personne n’est éliminé&nbsp;: à chaque ronde, les archers sont appariés selon le classement
        du moment — les vainqueurs entre eux, les battus entre eux. À effectif impair, un archer
        chôme à tour de rôle (le «&nbsp;bye&nbsp;»), et son tour de repos lui compte une victoire.
      </p>

      {/* CA — « le maximum que l'effectif du jour autorise, affiché en clair ». La borne existait
          déjà au domaine, mais l'organisateur ne la découvrait que par un refus (effectif déclaré)
          ou en voyant moins de rondes que prévu le jour J (le service borne à la lecture). */}
      {effectif !== null && reglage !== undefined && (
        <p className="carte__aide" role="status">
          {maximum === null
            ? decrireBorne(effectif, reglage.nb_rondes)
            : decrireBorneConnue(effectif, reglage.nb_rondes, maximum)}
        </p>
      )}

      {!estValide(etat) && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Indiquez un nombre de rondes entier, entre 1 et {RONDES_MAX_REGLABLES}.
        </span>
      )}
    </fieldset>
  )
}
