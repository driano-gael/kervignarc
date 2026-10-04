// Le **barème des duels** d'une étape (E01US011, ADR-0117), partagé par « Phases » et « Composer
// un format ». ⚠️ **Aucun état ici** : l'unique source est `etat`, détenu par le parent — même
// leçon que `ReglageSuisse`. Clé de liste par rang : les champs sont tous contrôlés.

import { useId } from 'react'

import type { EtatBareme, EtatBaremeDuel, EtatSurcharge, ModeDuel } from './baremeDuel'
import {
  BAREME_DUEL_NON_REGLE,
  DERNIERS_TOURS_MAX,
  FLECHES_MAX,
  MANCHES_MAX,
  derniersToursDepuis,
  ecartsDArmes,
  type ArmesConnues,
  estValide,
  libelleDerniersTours,
  presetClub,
  presetFfta,
  presetFftaEquipe,
  presetFftaMixte,
} from './baremeDuel'
import type { TypePhase } from './catalogue'

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
      <label className="formulaire__libelle">
        Flèches de barrage par camp
        <input
          inputMode="numeric"
          value={etat.barrage}
          onChange={(e) => surChangement({ ...etat, barrage: e.target.value })}
        />
      </label>
    </div>
  )
}

function ListeSurcharges({
  surcharges,
  surChangement,
  idListe,
  defaut,
  portee,
}: {
  surcharges: EtatSurcharge[]
  surChangement: (surcharges: EtatSurcharge[]) => void
  idListe: string
  defaut: EtatBareme
  /** Distingue au lecteur d'écran les surcharges des deux barèmes, rendues sur le même écran. */
  portee: string
}) {
  const changer = (index: number, partiel: Partial<EtatSurcharge>) =>
    surChangement(surcharges.map((s, i) => (i === index ? { ...s, ...partiel } : s)))
  return (
    <>
      <ul className="deroule__liste">
        {surcharges.map((surcharge, index) => (
          <li key={index}>
            <label className="formulaire__libelle">
              Arme
              <input
                list={idListe}
                value={surcharge.arme}
                onChange={(e) => changer(index, { arme: e.target.value })}
              />
            </label>
            <EditeurBareme
              libelle={`Barème de l’arme ${surcharge.arme || 'sans nom'}${portee}`}
              etat={surcharge.bareme}
              surChangement={(bareme) => changer(index, { bareme })}
            />
            <button
              type="button"
              className="bouton bouton--discret"
              aria-label={`Retirer la surcharge de l’arme ${surcharge.arme || 'sans nom'}${portee}`}
              onClick={() => surChangement(surcharges.filter((_, i) => i !== index))}
            >
              Retirer
            </button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="bouton bouton--discret"
        onClick={() => surChangement([...surcharges, { arme: '', bareme: { ...defaut } }])}
      >
        Ajouter une arme au barème propre{portee}
      </button>
    </>
  )
}

/**
 * `armes` : celles des catégories connues, pour pré-remplir les poulies d'un preset et signaler
 * les écarts — ou `'chargement'` / `'erreur'` : un preset posé sans elles oublierait les poulies,
 * donc les presets attendent. `sourceArmes` dit d'où elles viennent, pour nommer juste un écart.
 */
export function ReglageBaremeDuel({
  etat,
  surChangement,
  armes,
  sourceArmes,
  type,
}: {
  etat: EtatBaremeDuel
  surChangement: (etat: EtatBaremeDuel) => void
  armes: ArmesConnues
  sourceArmes: 'tournoi' | 'bibliotheque'
  type: TypePhase
}) {
  const idListe = useId()
  const connues = typeof armes === 'string' ? null : armes
  const presetsPossibles = connues !== null
  const ecarts = connues === null ? null : ecartsDArmes(etat, connues)
  const derniers = etat.derniers
  const nbDerniers = derniers === null ? NaN : Number(derniers.tours)
  const portee =
    derniers !== null && Number.isInteger(nbDerniers) && nbDerniers >= 1
      ? libelleDerniersTours(nbDerniers, type)
      : null

  return (
    <fieldset className="deroule__sources">
      <legend>Barème des duels</legend>

      <div className="formulaire__actions">
        <button
          type="button"
          className="bouton bouton--discret"
          disabled={!presetsPossibles}
          onClick={() => surChangement(presetFfta(connues ?? []))}
        >
          Preset FFTA officiel
        </button>
        <button
          type="button"
          className="bouton bouton--discret"
          disabled={!presetsPossibles}
          onClick={() => surChangement(presetClub(connues ?? []))}
        >
          Preset format club
        </button>
        <button
          type="button"
          className="bouton bouton--discret"
          disabled={!presetsPossibles}
          onClick={() => surChangement(presetFftaEquipe(connues ?? []))}
        >
          Preset FFTA équipe
        </button>
        <button
          type="button"
          className="bouton bouton--discret"
          disabled={!presetsPossibles}
          onClick={() => surChangement(presetFftaMixte(connues ?? []))}
        >
          Preset FFTA équipe mixte
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
      {armes === 'chargement' && (
        <p className="carte__aide">Chargement des armes des catégories avant les presets…</p>
      )}
      {armes === 'erreur' && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Armes des catégories indisponibles&nbsp;: presets désactivés. Les barèmes propres se
          saisissent à la main.
        </span>
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
          <ListeSurcharges
            surcharges={etat.surcharges}
            surChangement={(surcharges) => surChangement({ ...etat, surcharges })}
            idListe={idListe}
            defaut={etat.par_defaut}
            portee=""
          />
          <datalist id={idListe}>
            {(connues ?? []).map((arme) => (
              <option key={arme} value={arme} />
            ))}
          </datalist>

          <label className="formulaire__libelle">
            <input
              type="checkbox"
              checked={derniers !== null}
              onChange={(e) =>
                surChangement({
                  ...etat,
                  derniers: e.target.checked ? derniersToursDepuis(etat) : null,
                })
              }
            />
            Un autre barème pour les derniers tours
          </label>
          {derniers !== null && (
            <div role="group" aria-label="Barème des derniers tours">
              <label className="formulaire__libelle">
                Nombre de derniers tours
                <input
                  inputMode="numeric"
                  value={derniers.tours}
                  onChange={(e) =>
                    surChangement({ ...etat, derniers: { ...derniers, tours: e.target.value } })
                  }
                />
              </label>
              {portee !== null && (
                <p className="carte__aide">
                  Concerne {portee}.
                  {type === 'elimination_directe' &&
                    ' Un match de classement (petite finale, places 5 à 8…) joué à l’un de ces tours le suit aussi.'}
                </p>
              )}
              <EditeurBareme
                libelle="Barème par défaut des derniers tours"
                etat={derniers.par_defaut}
                surChangement={(par_defaut) =>
                  surChangement({ ...etat, derniers: { ...derniers, par_defaut } })
                }
              />
              <ListeSurcharges
                surcharges={derniers.surcharges}
                surChangement={(surcharges) =>
                  surChangement({ ...etat, derniers: { ...derniers, surcharges } })
                }
                idListe={idListe}
                defaut={derniers.par_defaut}
                portee=" (derniers tours)"
              />
            </div>
          )}
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
          {sourceArmes === 'tournoi'
            ? 'Aucune catégorie du tournoi ne porte ces armes, leur barème ne s’appliquera à personne'
            : 'Aucune catégorie de la bibliothèque ne porte ces armes : vérifiez qu’elles existeront dans le tournoi'}
          &nbsp;: {ecarts.surchargeOrpheline.join(', ')}.
        </span>
      )}
      {!estValide(etat) && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Complétez le barème&nbsp;: au plus {MANCHES_MAX} manches de {FLECHES_MAX} flèches au plus,
          de 1 à {FLECHES_MAX} flèches de barrage, un seuil atteignable en sets, une arme nommée une
          seule fois par barème, et de 1 à {DERNIERS_TOURS_MAX} derniers tours.
        </span>
      )}
    </fieldset>
  )
}
