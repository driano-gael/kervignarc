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
import type { Ronde } from './api'
import { ClassementSuisse } from './ClassementSuisse'
import { decrireBorneConnue } from '../../shared/phases/suisse'
import { ceQuiManque, decrirePlaces, etatRencontre, motDeLaFin } from './presentation'
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
  const mot = motDeLaFin(etat.data.rondes, rondesDues)

  return (
    <div>
      {/* La borne vient du **serveur** (`rondes_maximales`) et n'est jamais recalculée ici : deux
          arithmétiques pour une même règle divergent tôt ou tard. La rédaction, elle, est celle de
          `decrireBorne` — dont l'accord au singulier et le cas « moins de deux tireurs » ont été
          écrits et testés une fois pour toutes (corrigé en revue : cette ligne réimplémentait la
          phrase à la main et rendait « 1 archers … 0 ronde sans que deux archers se rencontrent
          deux fois », dont la raison invoquée était fausse). */}
      <p className="carte__aide">
        {decrireBorneConnue(etat.data.effectif, etat.data.nb_rondes, etat.data.rondes_maximales)}
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
          a plus rien à jouer » de « il reste des rencontres à saisir avant que la suite existe ».
          La condition vit dans `presentation.ts` — trois états, et le troisième (« se taire ») est
          celui qu'une condition écrite dans le JSX rend invisible au test. */}
      {mot?.etat === 'attente' && (
        <>
          <p className="carte__etat" role="status">
            La ronde {mot.suivante} sera appariée quand la ronde {mot.courante} sera{' '}
            <strong>entièrement</strong> saisie et validée : les adversaires se choisissent au
            classement du moment, donc ils ne peuvent pas être connus avant.
          </p>
          {/* CA E05US034 — **un refus dit ce qui manque**. La phrase ci-dessus explique la règle ;
              celle-ci nomme les rencontres, et distingue les deux attentes — une rencontre non
              saisie attend le scoreur de sa cible, une rencontre saisie et non validée attend un
              geste de validation. Les confondre renvoie chercher partout dans un gymnase où
              quatorze rencontres se jouent en parallèle (`P-3` : un refus sans issue est un
              cul-de-sac). */}
          <CeQuiManqueEncore rondes={etat.data.rondes} courante={mot.courante} />
        </>
      )}
      {mot?.etat === 'fini' && (
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
                {/* La place de tir **sur la ligne**, pas seulement dans le pavé ouvert (correctif
                    de revue) : en salle, on lit la liste pour aller à la butte, et la fiche de
                    recette le promettait déjà. Le jumeau poules l'affiche sur le titre du groupe —
                    ici c'est par rencontre, un suisse n'ayant qu'un bloc pour tout le plateau. */}
                {r.couloirs !== null && (
                  <span className="carte__aide"> — {decrirePlaces(r.couloirs)}</span>
                )}
              </span>
              <span className="duels-liste__etat">{etatRencontre(r)}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

/**
 * Ce qui empêche la ronde suivante d'exister, **nommé** (CA E05US034).
 *
 * ⚠️ **Ne rend rien quand rien ne manque** : la ronde peut être complète et close à la seconde où
 * l'écran se rafraîchit. Une liste vide sous une phrase d'attente serait contradictoire, et le
 * scoreur croirait à un bug de l'écran plutôt qu'à un décalage de dix secondes.
 */
function CeQuiManqueEncore({ rondes, courante }: { rondes: Ronde[]; courante: number }) {
  const ronde = rondes.find((r) => r.numero === courante)
  if (ronde === undefined) return null
  const manque = ceQuiManque(ronde.rencontres)
  if (
    manque.aSaisir.length +
      manque.aValider.length +
      manque.enFile.length +
      manque.bloquees.length ===
    0
  )
    return null

  return (
    <div className="carte__etat" role="status">
      {manque.aSaisir.length > 0 && (
        <p>
          <strong>Pas encore saisies</strong> ({manque.aSaisir.length})&nbsp;:{' '}
          {manque.aSaisir.join(' · ')}
        </p>
      )}
      {manque.aValider.length > 0 && (
        <p>
          <strong>Saisies, pas encore validées</strong> ({manque.aValider.length})&nbsp;:{' '}
          {manque.aValider.join(' · ')}
        </p>
      )}
      {manque.enFile.length > 0 && (
        <p>
          {/* Le geste est **fait**, il attend le réseau : la nommer autrement enverrait réclamer une
              validation déjà posée. La taire serait pire — si c'est la dernière rencontre, le
              résumé devient vide sous une phrase d'attente (correctif de revue, axe adversarial). */}
          <strong>Validées, en attente de réseau</strong> ({manque.enFile.length})&nbsp;:{' '}
          {manque.enFile.join(' · ')}
        </p>
      )}
      {manque.bloquees.length > 0 && (
        <p>
          {/* Ni saisie ni validation ne débloqueront celles-ci : le tir existe mais oppose d'autres
              duellistes (ADR-0049 §4). Les ranger avec les autres enverrait le scoreur buter sur un
              pavé que le serveur refuse d'écraser. */}
          <strong>Bloquées — population à rétablir</strong> ({manque.bloquees.length})&nbsp;:{' '}
          {manque.bloquees.join(' · ')}
        </p>
      )}
    </div>
  )
}
