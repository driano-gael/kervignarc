// Écran de saisie de la **colline** (E05US027, ADR-0083) — surface **scoreur**.
//
// Jumeau de `SaisieSuisse` par la coquille et **identique** par le pavé : un défi *est* un duel
// ordinaire (ADR-0083 §7), donc on remonte `DuelCharge` tel quel avec la famille `'colline'`. Ce
// qui diffère est la **navigation** — on entre par la **manche**, pas par une ronde ni par un
// numéro de match d'arbre : c'est le décor `RONDES_APPARIEES` du contrat de phase.
//
// Ce que le pavé apporte gratuitement : le mode (sets/cumul) résolu par l'arme, le barrage interne
// à un défi nul, le verrou de validation, l'état optimiste hors-ligne et le rejeu à la reconnexion
// (E04US009).
//
// ⚠️ **La manche suivante n'existe pas avant que la précédente soit close**, et la raison est plus
// forte encore qu'au suisse : les défis de la manche `n+1` se calculent sur les **positions**
// issues de la manche `n`. Tant qu'un défi n'est pas tranché, ces positions n'existent pas —
// apparier par-dessus ne donnerait pas un appariement approximatif mais un appariement **faux**.
// L'écran doit donc **nommer l'attente**, sans quoi le scoreur cherche une manche qui n'est nulle
// part et croit à une panne.

import { useState } from 'react'

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { usePhases } from '../saisie-duels/hooks'
import { DuelCharge } from '../saisie-duels/SaisieDuels'
import type { Manche } from './api'
import { ClassementColline } from './ClassementColline'
import { decrireBorneConnue } from '../../shared/phases/colline'
import {
  ceQuiManque,
  decrireDefi,
  decrirePlaces,
  etatDefi,
  motDeLaFin,
  nommerAuRepos,
  nommerFormat,
} from './presentation'
import { useEtatCollineSaisie } from './hooks'

export function SaisieColline({
  tournoiId,
  departId,
}: {
  tournoiId: number
  departId: number | null
}) {
  const phases = usePhases(departId)
  const [phaseId, setPhaseId] = useState<number | null>(null)

  const disponibles = (phases.data ?? []).filter((phase) => phase.type === 'colline')
  // Changer de créneau rend l'ancien `phaseId` étranger à la liste : le garder ferait scorer les
  // manches de l'autre départ, avec un identifiant valide et donc sans la moindre erreur.
  const phaseRetenue =
    phaseId !== null && disponibles.some((phase) => phase.id === phaseId) ? phaseId : null

  return (
    <div className="duels-saisie">
      <div className="duels-saisie__entete">
        <h3 className="carte__soustitre">Saisie de la colline</h3>
      </div>

      {phases.isError && <MessageErreur erreur={phases.error} />}
      {phases.isSuccess && disponibles.length === 0 && (
        <p className="carte__etat">
          Aucune phase de colline dans ce créneau : la saisie s’ouvrira quand une phase de ce type
          aura été composée et réglée.
        </p>
      )}
      {disponibles.length > 0 && (
        <select
          className="formulaire__champ"
          value={phaseRetenue ?? ''}
          onChange={(e) => setPhaseId(e.target.value === '' ? null : Number(e.target.value))}
          aria-label="Phase de colline à scorer"
        >
          <option value="">Choisir une phase…</option>
          {disponibles.map((phase) => (
            <option key={phase.id} value={phase.id}>
              Phase {phase.ordre} — colline
            </option>
          ))}
        </select>
      )}

      {/* `key` sur la phase : en changer **remonte** le sous-arbre (reset propre de la sélection). */}
      {phaseRetenue !== null && (
        <PhaseColline key={phaseRetenue} tournoiId={tournoiId} phaseId={phaseRetenue} />
      )}
    </div>
  )
}

function PhaseColline({ tournoiId, phaseId }: { tournoiId: number; phaseId: number }) {
  const etat = useEtatCollineSaisie(tournoiId, phaseId)
  const [ouvert, setOuvert] = useState<number | null>(null)

  if (etat.isPending) return <p className="carte__etat">Chargement des manches…</p>
  if (etat.isError) return <MessageErreur erreur={etat.error} />

  const defi =
    ouvert === null
      ? null
      : (etat.data.manches.flatMap((manche) => manche.defis).find((d) => d.numero === ouvert) ??
        null)

  if (defi !== null) {
    return (
      <div className="duel">
        <button type="button" className="lien duel__retour" onClick={() => setOuvert(null)}>
          ← Retour aux manches
        </button>
        {/* Le garde vaut aussi **pavé ouvert**, pas seulement à l'entrée : la population peut bouger
            pendant la saisie (un retardataire inscrit, un forfait), et le pavé se viderait sous les
            doigts du scoreur en gardant l'air prêt à saisir. Repris de `SaisieSuisse`. */}
        {defi.desynchronisee && (
          <p className="carte__etat carte__etat--alerte" role="status">
            Le tir enregistré sur ce défi oppose d’autres archers : la population de la phase a
            changé depuis. Demandez à l’organisateur de la rétablir — le score n’est pas perdu, il
            est mis de côté le temps que la colline redevienne celle de ce tir.
          </p>
        )}
        <p className="duel__entete">
          Manche {defi.manche} · {decrireDefi(defi.position_haute, defi.position_basse)}
          {defi.couloirs !== null && ` · ${decrirePlaces(defi.couloirs)}`}
        </p>
        {!defi.desynchronisee && (
          <DuelCharge
            tournoiId={tournoiId}
            phaseId={phaseId}
            matchNumero={defi.numero}
            duel={defi.duel}
            onValide={() => setOuvert(null)}
            famille="colline"
          />
        )}
      </div>
    )
  }

  const mot = motDeLaFin(etat.data.manches, etat.data.nb_manches)

  return (
    <div>
      <p className="carte__aide">
        {nommerFormat(etat.data.portee_de_defi)} — portée {etat.data.portee_de_defi}.
      </p>
      {/* La borne vient du **serveur** (`portee_maximale`) et n'est jamais recalculée ici : deux
          arithmétiques pour une même règle divergent tôt ou tard. La rédaction est celle de
          `decrireBorne`, dont l'accord au singulier et le cas « moins de deux tireurs » sont écrits
          et testés une fois pour toutes — c'est exactement la ligne que la revue du suisse a dû
          corriger pour l'avoir réimplémentée à la main. */}
      <p className="carte__aide">
        {decrireBorneConnue(
          etat.data.effectif,
          etat.data.portee_de_defi,
          etat.data.portee_maximale,
        )}
      </p>
      {etat.data.conflits.length > 0 && (
        // On **rapporte** le manque, on ne le comble pas : poser le bloc à la lecture reviendrait à
        // décider du placement dans un écran qui ne fait que lire (ADR-0083 §3).
        <p className="carte__etat carte__etat--alerte" role="status">
          Le plan de cibles n’est pas posé, ou la salle est trop petite ({etat.data.conflits.length}{' '}
          conflit(s)). L’organisateur doit le (re)générer.
        </p>
      )}

      {etat.data.manches.map((manche) => (
        <GroupeDeManche key={manche.numero} manche={manche} onOuvrir={setOuvert} />
      ))}

      {/* CA — « la manche suivante n'apparaît qu'une fois la précédente close, et l'écran le dit ».
          Sans cette phrase, il ne reste qu'une absence : le scoreur ne peut pas distinguer « il n'y
          a plus rien à jouer » de « il reste des défis à saisir avant que la suite existe ». */}
      {mot?.etat === 'attente' && (
        <>
          <p className="carte__etat" role="status">
            La manche {mot.suivante} sera appariée quand la manche {mot.courante} sera{' '}
            <strong>entièrement</strong> saisie et validée : les défis se calculent sur les
            positions issues de cette manche, donc ils ne peuvent pas être connus avant.
          </p>
          <CeQuiManqueEncore manches={etat.data.manches} courante={mot.courante} />
        </>
      )}
      {mot?.etat === 'fini' && (
        <p className="carte__etat" role="status">
          Toutes les manches sont jouées : la colline ci-dessous est définitive.
        </p>
      )}

      <ClassementColline classement={etat.data.classement} manches={etat.data.manches} />
    </div>
  )
}

function GroupeDeManche({
  manche,
  onOuvrir,
}: {
  manche: Manche
  onOuvrir: (numero: number) => void
}) {
  const auRepos = nommerAuRepos(manche)

  return (
    <section className="carte">
      <h4 className="carte__soustitre">
        Manche {manche.numero}
        {!manche.close && <span className="carte__aide"> — en cours</span>}
      </h4>

      {/* ⚠️ **Ce n'est pas un bye.** Un bye est un archer désigné qui gagne d'office ; ici personne
          ne gagne rien et personne ne bouge — ces archers n'ont simplement aucun défi cette
          manche-ci. Le dire est nécessaire : à portée 1 ce sont les **deux extrémités** de la
          colline une manche sur deux, quel que soit l'effectif, et sans cette ligne elles
          disparaissent sans explication pendant que le scoreur les cherche. */}
      {auRepos.length > 0 && (
        <p className="carte__aide">
          Au repos cette manche : {auRepos.join(' · ')}. Personne ne marque et personne ne bouge —
          ils rejouent la manche suivante.
        </p>
      )}

      <ul className="duels-liste">
        {manche.defis.map((d) => (
          <li key={d.numero}>
            <button
              type="button"
              className="duels-liste__ligne"
              // ⚠️ **Un défi désynchronisé ne s'ouvre pas** : il s'afficherait « à tirer », et le
              // service le refuserait en 409 au premier enregistrement — l'écran tendrait le piège.
              // On bloque l'entrée plutôt que de faire découvrir le refus une flèche plus tard.
              disabled={d.desynchronisee}
              onClick={() => onOuvrir(d.numero)}
            >
              <span className="duels-liste__nom">
                {/* Les **positions** d'abord : c'est le vocabulaire du format, et ce que le public
                    suit. « MARTIN contre DURAND » perdrait qui défie qui. */}
                <strong>{decrireDefi(d.position_haute, d.position_basse)}</strong> —{' '}
                {d.haut ? `${d.haut.nom} ${d.haut.prenom}` : '—'} contre{' '}
                {d.bas ? `${d.bas.nom} ${d.bas.prenom}` : '—'}
                {d.couloirs !== null && (
                  <span className="carte__aide"> — {decrirePlaces(d.couloirs)}</span>
                )}
              </span>
              <span className="duels-liste__etat">{etatDefi(d)}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

/**
 * Ce qui empêche la manche suivante d'exister, **nommé**.
 *
 * ⚠️ **Ne rend rien quand rien ne manque** : la manche peut être complète et close à la seconde où
 * l'écran se rafraîchit. Une liste vide sous une phrase d'attente serait contradictoire, et le
 * scoreur croirait à un bug de l'écran plutôt qu'à un décalage de dix secondes.
 */
function CeQuiManqueEncore({ manches, courante }: { manches: Manche[]; courante: number }) {
  const manche = manches.find((m) => m.numero === courante)
  if (manche === undefined) return null
  const manque = ceQuiManque(manche.defis)
  if (
    manque.aSaisir.length +
      manque.aValider.length +
      manque.enFile.length +
      manque.bloques.length ===
    0
  )
    return null

  return (
    <div className="carte__etat" role="status">
      {manque.aSaisir.length > 0 && (
        <p>
          <strong>Pas encore saisis</strong> ({manque.aSaisir.length})&nbsp;:{' '}
          {manque.aSaisir.join(' · ')}
        </p>
      )}
      {manque.aValider.length > 0 && (
        <p>
          <strong>Saisis, pas encore validés</strong> ({manque.aValider.length})&nbsp;:{' '}
          {manque.aValider.join(' · ')}
        </p>
      )}
      {manque.enFile.length > 0 && (
        <p>
          {/* Le geste est **fait**, il attend le réseau : le nommer autrement enverrait réclamer une
              validation déjà posée. Le taire serait pire — si c'est le dernier défi, le résumé
              devient vide sous une phrase d'attente. */}
          <strong>Validés, en attente de réseau</strong> ({manque.enFile.length})&nbsp;:{' '}
          {manque.enFile.join(' · ')}
        </p>
      )}
      {manque.bloques.length > 0 && (
        <p>
          {/* Ni saisie ni validation ne débloqueront ceux-ci : le tir existe mais oppose d'autres
              duellistes (ADR-0049 §4). */}
          <strong>Bloqués — population à rétablir</strong> ({manque.bloques.length})&nbsp;:{' '}
          {manque.bloques.join(' · ')}
        </p>
      )}
    </div>
  )
}
