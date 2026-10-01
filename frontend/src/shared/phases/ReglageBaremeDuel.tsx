// Le **barème des duels** d'une étape (E01US011, ADR-0117), partagé par « Phases » et « Composer
// un format ». ⚠️ **Aucun état ici** : l'unique source est `etat`, détenu par le parent — même
// leçon que `ReglageSuisse`. Clé de liste par rang : les champs sont tous contrôlés.

import { useId } from 'react'

import type { EtatBareme, EtatBaremeDuel, ModeDuel } from './baremeDuel'
import {
  BAREME_DUEL_NON_REGLE,
  FLECHES_MAX,
  MANCHES_MAX,
  ecartsDArmes,
  estValide,
  presetClub,
  presetFfta,
} from './baremeDuel'

function EditeurBareme({
  etat,
  surChangement,
  libelle,
}: {
  etat: EtatBareme
  surChangement: (etat: EtatBareme) => void
  libelle: string
}) {
  return (
    <div className="formulaire__actions" role="group" aria-label={libelle}>
      <label className="formulaire__libelle">
        Mode
        <select
          value={etat.mode}
          onChange={(e) => surChangement({ ...etat, mode: e.target.value as ModeDuel })}
        >
          <option value="sets">Sets (points de set)</option>
          <option value="cumul">Cumul des points</option>
        </select>
      </label>
      <label className="formulaire__libelle">
        Manches
        <input
          inputMode="numeric"
          value={etat.manches}
          onChange={(e) => surChangement({ ...etat, manches: e.target.value })}
        />
      </label>
      <label className="formulaire__libelle">
        Flèches par manche
        <input
          inputMode="numeric"
          value={etat.fleches}
          onChange={(e) => surChangement({ ...etat, fleches: e.target.value })}
        />
      </label>
      {etat.mode === 'sets' && (
        <label className="formulaire__libelle">
          Points pour gagner
          <input
            inputMode="numeric"
            value={etat.points}
            onChange={(e) => surChangement({ ...etat, points: e.target.value })}
          />
        </label>
      )}
    </div>
  )
}

/**
 * `armes` : celles des catégories connues, pour pré-remplir les poulies d'un preset et signaler
 * les écarts. `null` tant qu'elles ne sont pas chargées : un preset posé à ce moment-là oublierait
 * les poulies, donc les presets attendent.
 */
export function ReglageBaremeDuel({
  etat,
  surChangement,
  armes,
}: {
  etat: EtatBaremeDuel
  surChangement: (etat: EtatBaremeDuel) => void
  armes: readonly string[] | null
}) {
  const idListe = useId()
  const presetsPossibles = armes !== null
  const ecarts = armes === null ? null : ecartsDArmes(etat, armes)
  const changerSurcharge = (
    index: number,
    partiel: Partial<EtatBaremeDuel['surcharges'][number]>,
  ) =>
    surChangement({
      ...etat,
      surcharges: etat.surcharges.map((s, i) => (i === index ? { ...s, ...partiel } : s)),
    })

  return (
    <fieldset className="deroule__sources">
      <legend>Barème des duels</legend>

      <div className="formulaire__actions">
        <button
          type="button"
          className="bouton bouton--discret"
          disabled={!presetsPossibles}
          onClick={() => surChangement(presetFfta(armes ?? []))}
        >
          Preset FFTA officiel
        </button>
        <button
          type="button"
          className="bouton bouton--discret"
          disabled={!presetsPossibles}
          onClick={() => surChangement(presetClub(armes ?? []))}
        >
          Preset format club
        </button>
        {etat.regle && (
          <button
            type="button"
            className="bouton bouton--discret"
            onClick={() => surChangement(BAREME_DUEL_NON_REGLE)}
          >
            Revenir au barème par défaut
          </button>
        )}
      </div>
      {!presetsPossibles && (
        <p className="carte__aide">Chargement des armes des catégories avant les presets…</p>
      )}

      {!etat.regle ? (
        <p className="carte__aide">
          Barème par défaut&nbsp;: sets en 5 manches de 3 flèches, premier à 6 points&nbsp;; les
          arcs dont le nom contient «&nbsp;poulie&nbsp;» ou «&nbsp;compound&nbsp;» tirent au cumul.
        </p>
      ) : (
        <>
          <EditeurBareme
            libelle="Barème par défaut"
            etat={etat.par_defaut}
            surChangement={(par_defaut) => surChangement({ ...etat, par_defaut })}
          />

          <p className="carte__aide">
            Une arme listée ci-dessous tire avec son propre barème. Son nom est celui de la
            catégorie — majuscules et espaces en bord ne comptent pas.
          </p>
          <ul className="deroule__liste">
            {etat.surcharges.map((surcharge, index) => (
              <li key={index}>
                <label className="formulaire__libelle">
                  Arme
                  <input
                    list={idListe}
                    value={surcharge.arme}
                    onChange={(e) => changerSurcharge(index, { arme: e.target.value })}
                  />
                </label>
                <EditeurBareme
                  libelle={`Barème de l’arme ${surcharge.arme || 'sans nom'}`}
                  etat={surcharge.bareme}
                  surChangement={(bareme) => changerSurcharge(index, { bareme })}
                />
                <button
                  type="button"
                  className="bouton bouton--discret"
                  aria-label={`Retirer la surcharge de l’arme ${surcharge.arme || 'sans nom'}`}
                  onClick={() =>
                    surChangement({
                      ...etat,
                      surcharges: etat.surcharges.filter((_, i) => i !== index),
                    })
                  }
                >
                  Retirer
                </button>
              </li>
            ))}
          </ul>
          <datalist id={idListe}>
            {(armes ?? []).map((arme) => (
              <option key={arme} value={arme} />
            ))}
          </datalist>
          <button
            type="button"
            className="bouton bouton--discret"
            onClick={() =>
              surChangement({
                ...etat,
                surcharges: [...etat.surcharges, { arme: '', bareme: { ...etat.par_defaut } }],
              })
            }
          >
            Ajouter une arme au barème propre
          </button>
        </>
      )}

      <p className="carte__aide">
        Le barème se fige dès qu’un duel de la phase a été tiré&nbsp;: il ne se modifie plus
        ensuite.
      </p>

      {ecarts !== null && ecarts.poulieSansSurcharge.length > 0 && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Sans barème propre, ces arcs à poulies tireront au barème par défaut, en sets&nbsp;:{' '}
          {ecarts.poulieSansSurcharge.join(', ')}.
        </span>
      )}
      {ecarts !== null && ecarts.surchargeOrpheline.length > 0 && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Aucune catégorie ne porte ces armes, leur barème ne s’appliquera à personne&nbsp;:{' '}
          {ecarts.surchargeOrpheline.join(', ')}.
        </span>
      )}
      {!estValide(etat) && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Complétez le barème&nbsp;: au plus {MANCHES_MAX} manches de {FLECHES_MAX} flèches au plus,
          un seuil atteignable en sets, et une arme nommée une seule fois.
        </span>
      )}
    </fieldset>
  )
}
