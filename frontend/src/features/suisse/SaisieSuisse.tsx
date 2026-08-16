// Écran de saisie du **système suisse** (E05US030, ADR-0083) — surface **scoreur**.
//
// Jumeau de `SaisiePoules` par la coquille et **identique** par le pavé : une rencontre de ronde
// *est* un duel ordinaire (ADR-0083 §7), donc on remonte `DuelCharge` tel quel avec la famille
// `'suisse'`. Ce qui diffère est la **navigation** — on entre par la **ronde**, pas par un numéro de
// match d'arbre : c'est le décor `RONDES_APPARIEES` du contrat de phase.
//
// Ce que le pavé apporte gratuitement : le mode (sets/cumul) résolu par l'arme, le barrage interne à
// une rencontre nulle, le verrou de validation, l'état optimiste hors-ligne et le rejeu à la
// reconnexion (E04US009).
//
// ⚠️ **La ronde suivante n'existe pas avant que la précédente soit close**, et c'est structurel :
// le moteur refuse d'apparier par-dessus une ronde en cours (`domain/suisse.py::_rondes_closes`),
// puisqu'un appariement suisse se calcule sur le classement du moment. L'écran doit donc **nommer
// l'attente** — sans quoi le scoreur cherche une ronde qui n'est nulle part et croit à une panne.

import { useState } from 'react'

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { usePhases } from '../saisie-duels/hooks'
import { DuelCharge } from '../saisie-duels/SaisieDuels'
import type { Place } from '../poules/api'
import type { RangSuisse, RencontreSuisse, Ronde } from './api'
import { useEtatSuisseSaisie } from './hooks'

export function SaisieSuisse({
  tournoiId,
  departId,
}: {
  tournoiId: number
  departId: number | null
}) {
  const phases = usePhases(departId)
  const [phaseId, setPhaseId] = useState<number | null>(null)

  const disponibles = (phases.data ?? []).filter((phase) => phase.type === 'suisse')
  // Changer de créneau rend l'ancien `phaseId` étranger à la liste : le garder ferait scorer les
  // rondes de l'autre départ, avec un identifiant valide et donc sans la moindre erreur.
  const phaseRetenue =
    phaseId !== null && disponibles.some((phase) => phase.id === phaseId) ? phaseId : null

  return (
    <div className="duels-saisie">
      <div className="duels-saisie__entete">
        <h3 className="carte__soustitre">Saisie du système suisse</h3>
      </div>

      {phases.isError && <MessageErreur erreur={phases.error} />}
      {phases.isSuccess && disponibles.length === 0 && (
        <p className="carte__etat">
          Aucune phase au système suisse dans ce créneau : la saisie s’ouvrira quand une phase de ce
          type aura été composée et réglée.
        </p>
      )}
      {disponibles.length > 0 && (
        <select
          className="formulaire__champ"
          value={phaseRetenue ?? ''}
          onChange={(e) => setPhaseId(e.target.value === '' ? null : Number(e.target.value))}
          aria-label="Phase au système suisse à scorer"
        >
          <option value="">Choisir une phase…</option>
          {disponibles.map((phase) => (
            <option key={phase.id} value={phase.id}>
              Phase {phase.ordre} — système suisse
            </option>
          ))}
        </select>
      )}

      {/* `key` sur la phase : en changer **remonte** le sous-arbre (reset propre de la sélection). */}
      {phaseRetenue !== null && (
        <PhaseSuisse key={phaseRetenue} tournoiId={tournoiId} phaseId={phaseRetenue} />
      )}
    </div>
  )
}

function PhaseSuisse({ tournoiId, phaseId }: { tournoiId: number; phaseId: number }) {
  const etat = useEtatSuisseSaisie(tournoiId, phaseId)
  const [ouverte, setOuverte] = useState<number | null>(null)

  if (etat.isPending) return <p className="carte__etat">Chargement des rondes…</p>
  if (etat.isError) return <MessageErreur erreur={etat.error} />

  const rencontre =
    ouverte === null
      ? null
      : (etat.data.rondes.flatMap((ronde) => ronde.rencontres).find((r) => r.numero === ouverte) ??
        null)

  if (rencontre !== null) {
    return (
      <div className="duel">
        <button type="button" className="lien duel__retour" onClick={() => setOuverte(null)}>
          ← Retour aux rondes
        </button>
        {/* Le garde vaut aussi **pavé ouvert**, pas seulement à l'entrée : la population peut bouger
            pendant la saisie (un retardataire inscrit, un forfait), et le pavé se viderait sous les
            doigts du scoreur en gardant l'air prêt à saisir. Repris de `SaisiePoules`. */}
        {rencontre.desynchronisee && (
          <p className="carte__etat carte__etat--alerte" role="status">
            Le tir enregistré sur cette rencontre oppose d’autres archers : la population de la
            phase a changé depuis. Demandez à l’organisateur de la rétablir — le score n’est pas
            perdu, il est mis de côté le temps que les rondes redeviennent celles de ce tir.
          </p>
        )}
        <p className="duel__entete">
          Ronde {rencontre.ronde}
          {rencontre.couloirs !== null && ` · ${decrirePlaces(rencontre.couloirs)}`}
        </p>
        {!rencontre.desynchronisee && (
          <DuelCharge
            tournoiId={tournoiId}
            phaseId={phaseId}
            matchNumero={rencontre.numero}
            duel={rencontre.duel}
            onValide={() => setOuverte(null)}
            famille="suisse"
          />
        )}
      </div>
    )
  }

  const rondesDues = Math.min(etat.data.nb_rondes, etat.data.rondes_maximales)
  const derniere = etat.data.rondes[etat.data.rondes.length - 1] ?? null

  return (
    <div>
      <p className="carte__aide">
        {etat.data.effectif} archers, {rondesDues} ronde(s) à jouer
        {etat.data.nb_rondes > etat.data.rondes_maximales &&
          ` (${etat.data.nb_rondes} réglées, mais l’effectif n’en permet que ${etat.data.rondes_maximales} sans que deux archers se rencontrent deux fois)`}
        .
      </p>
      {etat.data.conflits.length > 0 && (
        // On **rapporte** le manque, on ne le comble pas : poser le bloc à la lecture reviendrait à
        // décider du placement dans un écran qui ne fait que lire (ADR-0083 §3).
        <p className="carte__etat carte__etat--alerte" role="status">
          Le plan de cibles n’est pas posé, ou la salle est trop petite ({etat.data.conflits.length}{' '}
          conflit(s)). L’organisateur doit le (re)générer.
        </p>
      )}

      {etat.data.rondes.map((ronde) => (
        <GroupeDeRonde key={ronde.numero} ronde={ronde} onOuvrir={setOuverte} />
      ))}

      {/* CA — « la ronde suivante n'apparaît qu'une fois la précédente close, et l'écran le dit ».
          Sans cette phrase, il ne reste qu'une absence : le scoreur ne peut pas distinguer « il n'y
          a plus rien à jouer » de « il reste des rencontres à saisir avant que la suite existe ». */}
      {derniere !== null && !derniere.close && etat.data.rondes.length < rondesDues && (
        <p className="carte__etat" role="status">
          La ronde {derniere.numero + 1} sera appariée quand la ronde {derniere.numero} sera{' '}
          <strong>entièrement</strong> saisie et validée : les adversaires se choisissent au
          classement du moment, donc ils ne peuvent pas être connus avant.
        </p>
      )}
      {etat.data.rondes.length >= rondesDues &&
        derniere !== null &&
        derniere.close &&
        rondesDues > 0 && (
          <p className="carte__etat" role="status">
            Toutes les rondes sont jouées : le classement ci-dessous est définitif.
          </p>
        )}

      <ClassementSuisse classement={etat.data.classement} rondes={etat.data.rondes} />
    </div>
  )
}

function GroupeDeRonde({ ronde, onOuvrir }: { ronde: Ronde; onOuvrir: (numero: number) => void }) {
  return (
    <section className="carte">
      <h4 className="carte__soustitre">
        Ronde {ronde.numero}
        {!ronde.close && <span className="carte__aide"> — en cours</span>}
      </h4>

      {/* Le porteur du bye. Il ne tire pas et compte une victoire : le dire est nécessaire, sans
          quoi l'archer se croit oublié et le scoreur cherche une rencontre qui n'existe pas. */}
      {ronde.bye !== null && (
        <p className="carte__aide">
          {ronde.bye.nom} {ronde.bye.prenom} ne tire pas cette ronde (bye) : elle lui compte une
          victoire.
        </p>
      )}

      <ul className="duels-liste">
        {ronde.rencontres.map((r) => (
          <li key={r.numero}>
            <button
              type="button"
              className="duels-liste__ligne"
              // ⚠️ **Une rencontre désynchronisée ne s'ouvre pas** : elle s'afficherait « à tirer »,
              // et le service la refuserait en 409 au premier enregistrement — l'écran tendrait le
              // piège. On bloque l'entrée plutôt que de faire découvrir le refus une flèche plus
              // tard (leçon d'E05US023).
              disabled={r.desynchronisee}
              onClick={() => onOuvrir(r.numero)}
            >
              <span className="duels-liste__nom">
                {r.haut ? `${r.haut.nom} ${r.haut.prenom}` : '—'} contre{' '}
                {r.bas ? `${r.bas.nom} ${r.bas.prenom}` : '—'}
              </span>
              <span className="duels-liste__etat">{etatRencontre(r)}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

/** Le classement **provisoire**, relu après chaque ronde close (CA du 16/08/2026).
 *
 * C'est la seule lecture d'avancement d'un format sans arbre : personne n'est éliminé, donc rien
 * dans la liste des rondes ne dit qui mène. Et c'est aussi ce qui **explique** les appariements de
 * la ronde suivante, qui s'y lisent d'avance.
 */
function ClassementSuisse({ classement, rondes }: { classement: RangSuisse[]; rondes: Ronde[] }) {
  if (classement.length === 0) return null
  const nom = (archerId: number) => {
    for (const ronde of rondes) {
      for (const r of ronde.rencontres) {
        if (r.haut?.archer_id === archerId) return `${r.haut.nom} ${r.haut.prenom}`
        if (r.bas?.archer_id === archerId) return `${r.bas.nom} ${r.bas.prenom}`
      }
      if (ronde.bye?.archer_id === archerId) return `${ronde.bye.nom} ${ronde.bye.prenom}`
    }
    return `#${archerId}`
  }

  return (
    <table className="deroule__table">
      <caption>Classement après {rondes.filter((r) => r.close).length} ronde(s)</caption>
      <thead>
        <tr>
          <th>Rang</th>
          <th>Archer</th>
          <th>Points</th>
          <th>Buchholz</th>
        </tr>
      </thead>
      <tbody>
        {classement.map((ligne) => (
          <tr key={ligne.archer_id}>
            <td>
              {ligne.rang}
              {ligne.ex_aequo ? ' =' : ''}
            </td>
            <td>{nom(ligne.archer_id)}</td>
            <td>{decrirePoints(ligne.points)}</td>
            <td>{decrirePoints(ligne.buchholz)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** Les points, rendus **en points réels**.
 *
 * ⚠️ Le serveur les transporte en **demi-points doublés** (victoire = 2, nul = 1) pour ne comparer
 * que des entiers — une égalité de départage ne doit pas reposer sur un flottant. C'est donc à
 * l'affichage de rendre la moitié : servir le nombre brut annoncerait « 6 victoires » à qui en a
 * trois.
 */
function decrirePoints(doubles: number): string {
  return doubles % 2 === 0 ? String(doubles / 2) : `${Math.floor(doubles / 2)},5`
}

/** Des places de tir en toutes lettres, **groupées par cible** (repris de `SaisiePoules`).
 *
 * Un bloc de couloirs est contigu dans la salle *mise à plat*, pas sur une seule cible : les deux
 * places d'une rencontre peuvent chevaucher deux cibles.
 */
function decrirePlaces(places: readonly Place[]): string {
  const parCible = new Map<number, string[]>()
  for (const [cible, couloir] of places) {
    parCible.set(cible, [...(parCible.get(cible) ?? []), couloir])
  }
  return [...parCible.entries()]
    .map(([cible, couloirs]) => `cible ${cible} : ${couloirs.join(', ')}`)
    .join(' · ')
}

/** L'état d'une rencontre en un mot — le même vocabulaire que les duels et les poules. */
function etatRencontre(rencontre: RencontreSuisse): string {
  if (rencontre.desynchronisee) return 'tir mis de côté — population à rétablir'
  const duel = rencontre.duel
  if (duel.validee_par !== null) return 'validée'
  if (duel.validation_en_attente === true) return 'validation en attente'
  if (duel.resultat?.termine === true) return 'à valider'
  if (duel.manches.length > 0) return 'en cours'
  return 'à tirer'
}
