// ⚠️ **`// DETTE-079` — la coquille de ce panneau est écrite TROIS fois** (ici, `SaisieSuisse`, `SaisieColline`), à
// l'identique sur ~120 lignes. Toute correction faite ici se porte sur les deux autres, et **rien
// ne rougira** si elle ne l'est qu'à une : cinq correctifs de revue ont déjà voyagé à la main d'un
// écran à l'autre. Le remède retenu est « rien » — la liste des formats à rencontres est close
// (`DETTE-066`) —, donc la trace au registre EST le garde-fou.
// Écran de saisie des **rencontres de poule** (E05US023, ADR-0083) — surface **scoreur**.
//
// Jumeau de `SaisieDuels` par la coquille (choisir un créneau, puis une phase), et **identique** par
// le pavé : une rencontre de poule *est* un duel ordinaire (ADR-0083 §7), donc on remonte
// `DuelCharge` tel quel avec la famille `'poule'`. Ce qui diffère est la **navigation** — on entre
// par la poule et le tour, pas par le numéro de match d'un arbre —, et c'est tout ce que ce fichier
// écrit de neuf.
//
// Ce que le pavé apporte gratuitement, et qu'il aurait fallu réécrire sinon : le mode (sets/cumul)
// résolu par l'arme, le barrage interne à une rencontre nulle, le verrou de validation, l'état
// optimiste hors-ligne et le rejeu à la reconnexion (E04US009).

import { useState } from 'react'

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { usePhases } from '../saisie-duels/hooks'
import { DuelCharge } from '../saisie-duels/SaisieDuels'
import { decrirePlaces } from '../../shared/salle/place'
// E05US027 : la fonction vivait ici, à l'identique de celle du suisse. La colline en faisait la
// 3ᵉ occurrence, donc elle est remontée en `shared/` — le rendez-vous posé par la revue d'E05US030.
import { etatRencontreDeSaisie as etatRencontre } from '../../shared/duels/etatDeSaisie'
import type { Poule } from './api'
import { useEtatPoulesSaisie } from './hooks'
import { decrireRepartition } from '../../shared/phases/poules'

export function SaisiePoules({
  tournoiId,
  departId,
}: {
  tournoiId: number
  departId: number | null
}) {
  const phases = usePhases(departId)
  const [phaseId, setPhaseId] = useState<number | null>(null)

  const poulesDispo = (phases.data ?? []).filter((phase) => phase.type === 'poules')

  // ⚠️ **Toujours pas de `return null` ici**, et la raison a survécu au remède de `DETTE-056`
  // (E05US030, qui a remonté le créneau dans l'espace scoreur). Une première tentative — E05US023 —
  // masquait tout le panneau quand le créneau ne portait aucune poule, pour supprimer le second
  // sélecteur de créneau : elle créait un cul-de-sac, le sélecteur vivant *dans* le JSX retiré.
  // Le sélecteur n'est plus ici, mais masquer resterait faux pour l'autre moitié du défaut : la
  // branche d'erreur deviendrait morte, et un `/phases` en échec ferait disparaître le panneau
  // **sans un mot**, en salle, wifi instable.
  //
  // Changer de créneau rend l'ancien `phaseId` étranger à la liste : le garder ferait scorer les
  // poules de l'autre départ, avec un identifiant valide et donc sans la moindre erreur.
  const phaseRetenue =
    phaseId !== null && poulesDispo.some((phase) => phase.id === phaseId) ? phaseId : null

  return (
    <div className="duels-saisie">
      <div className="duels-saisie__entete">
        <h3 className="carte__soustitre">Saisie des poules</h3>
      </div>

      {phases.isError && <MessageErreur erreur={phases.error} />}
      {phases.isSuccess && poulesDispo.length === 0 && (
        <p className="carte__etat">
          Aucune phase de poules dans ce créneau : la saisie s’ouvrira quand une phase de poules
          aura été composée et réglée.
        </p>
      )}
      {poulesDispo.length > 0 && (
        <select
          className="formulaire__champ"
          value={phaseRetenue ?? ''}
          onChange={(e) => setPhaseId(e.target.value === '' ? null : Number(e.target.value))}
          aria-label="Phase de poules à scorer"
        >
          <option value="">Choisir une phase…</option>
          {poulesDispo.map((phase) => (
            <option key={phase.id} value={phase.id}>
              Phase {phase.ordre} — poules
            </option>
          ))}
        </select>
      )}

      {/* `key` sur la phase : en changer **remonte** le sous-arbre (reset propre de la sélection). */}
      {phaseRetenue !== null && (
        <PhaseDePoules key={phaseRetenue} tournoiId={tournoiId} phaseId={phaseRetenue} />
      )}
    </div>
  )
}

function PhaseDePoules({ tournoiId, phaseId }: { tournoiId: number; phaseId: number }) {
  const etat = useEtatPoulesSaisie(tournoiId, phaseId)
  const [ouverte, setOuverte] = useState<number | null>(null)

  if (etat.isPending) return <p className="carte__etat">Chargement des poules…</p>
  if (etat.isError) return <MessageErreur erreur={etat.error} />

  const rencontre =
    ouverte === null
      ? null
      : (etat.data.poules.flatMap((poule) => poule.rencontres).find((r) => r.numero === ouverte) ??
        null)

  if (rencontre !== null) {
    return (
      <div className="duel">
        <button type="button" className="lien duel__retour" onClick={() => setOuverte(null)}>
          ← Retour aux poules
        </button>
        {/* ⚠️ Le garde vaut aussi **pavé ouvert**, pas seulement à l'entrée. La rencontre peut se
            désynchroniser pendant la saisie — l'organisateur inscrit un retardataire, le refetch
            qui suit l'enregistrement d'une manche recompose les poules — et le pavé se viderait
            sous les doigts du scoreur en gardant l'air prêt à saisir. C'est le piège même que
            l'écran ferme un cran plus haut (correctif de revue). */}
        {rencontre.desynchronisee && (
          <p className="carte__etat carte__etat--alerte" role="status">
            Le tir enregistré sur cette rencontre oppose d’autres archers : la composition de la
            poule a changé depuis. Demandez à l’organisateur de rétablir la population du créneau —
            le score n’est pas perdu, il est mis de côté le temps que les poules redeviennent celles
            de ce tir.
          </p>
        )}
        <p className="duel__entete">
          Poule {rencontre.poule} · tour {rencontre.tour}
          {rencontre.couloirs !== null && ` · ${decrirePlaces(rencontre.couloirs)}`}
        </p>
        {!rencontre.desynchronisee && (
          <DuelCharge
            tournoiId={tournoiId}
            phaseId={phaseId}
            matchNumero={rencontre.numero}
            duel={rencontre.duel}
            onValide={() => setOuverte(null)}
            famille="poule"
          />
        )}
      </div>
    )
  }

  return (
    <div>
      <p className="carte__aide">
        {/* Le mode est **dit** au scoreur (E05US029) : sur une phase de niveau, les groupes ne
            sont pas équilibrés, et un scoreur qui verrait la poule A aligner les six meilleurs
            sans explication pourrait croire à une composition ratée. */}
        {etat.data.repartition.effectif} archers,{' '}
        {etat.data.repartition.mode === 'par_niveau' && etat.data.repartition.tailles.length > 0
          ? `${decrireRepartition(etat.data.repartition.tailles, 'par_niveau')} de la phase`
          : `${etat.data.repartition.nb_poules} poules de ${etat.data.repartition.taille_visee} visés`}
        .
      </p>
      {etat.data.conflits.length > 0 && (
        // On **rapporte** le manque, on ne le comble pas : poser une poule à la lecture reviendrait
        // à décider du placement dans un écran qui ne fait que lire (ADR-0083 §3).
        <p className="carte__etat carte__etat--alerte" role="status">
          {etat.data.conflits.length} poule(s) sans couloirs : le plan de cibles n’est pas posé, ou
          la salle est trop petite. L’organisateur doit le (re)générer.
        </p>
      )}
      {etat.data.poules.map((poule) => (
        <GroupeDePoule key={poule.numero} poule={poule} onOuvrir={setOuverte} />
      ))}
    </div>
  )
}

function GroupeDePoule({ poule, onOuvrir }: { poule: Poule; onOuvrir: (numero: number) => void }) {
  const nom = (archerId: number) => {
    const membre = poule.membres.find((m) => m.archer_id === archerId)
    return membre ? `${membre.nom} ${membre.prenom}` : `#${archerId}`
  }
  // Les rencontres sont présentées **par tour** — l'ordre que le moteur produit déjà, et c'est lui
  // qui garantit qu'un archer ne figure pas deux fois dans le même tour, donc que le tour se tire
  // en parallèle sur le bloc de couloirs de la poule.
  const tours = [...new Set(poule.rencontres.map((r) => r.tour))].sort((a, b) => a - b)

  return (
    <section className="carte">
      <h4 className="carte__soustitre">
        Poule {poule.numero}
        {poule.bloc !== null && poule.bloc.length > 0 && (
          <span className="carte__aide"> — {decrirePlaces(poule.bloc)}</span>
        )}
      </h4>

      {/* CA — « le barrage se tire et se saisit ». L'annonce vit ici, sur la poule concernée ; le
          tir lui-même se fait au panneau de barrages (portée « poule », E06US003), qui sait
          annoncer, faire tirer et clore. Dupliquer la saisie ici aurait fait deux barrages. */}
      {poule.barrage_requis && (
        <p className="carte__etat carte__etat--alerte" role="status">
          Barrage requis : les cinq critères du départage n’ont pas séparé cette poule
          {rangsExAequo(poule).length > 0 && ` (rang ${rangsExAequo(poule).join(', ')})`}. Faites-le
          tirer depuis « Départager les archers » (portée poule) — indiquez cette phase et ce rang,
          c’est ce qui permet au verdict de refermer ce classement.
        </p>
      )}

      {tours.map((tour) => (
        <div key={tour}>
          <p className="duel__manche-titre">Tour {tour}</p>
          <ul className="duels-liste">
            {poule.rencontres
              .filter((r) => r.tour === tour)
              .map((r) => (
                <li key={r.numero}>
                  <button
                    type="button"
                    className="duels-liste__ligne"
                    // ⚠️ **Une rencontre désynchronisée ne s'ouvre pas.** Elle s'affichait « à
                    // tirer », indiscernable d'une rencontre jamais commencée, et le service la
                    // refusait en 409 au premier enregistrement — l'écran tendait le piège. On
                    // bloque l'entrée plutôt que de faire découvrir le refus une flèche plus tard.
                    disabled={r.desynchronisee}
                    onClick={() => onOuvrir(r.numero)}
                  >
                    <span className="duels-liste__nom">
                      {r.duel.haut ? `${r.duel.haut.nom} ${r.duel.haut.prenom}` : '—'} contre{' '}
                      {r.duel.bas ? `${r.duel.bas.nom} ${r.duel.bas.prenom}` : '—'}
                    </span>
                    <span className="duels-liste__etat">{etatRencontre(r)}</span>
                  </button>
                </li>
              ))}
          </ul>
        </div>
      ))}

      <table className="deroule__table">
        <caption>Classement de la poule</caption>
        <thead>
          <tr>
            <th>Rang</th>
            <th>Archer</th>
            <th>Pts</th>
            <th>Δ sets</th>
            <th>Δ score</th>
          </tr>
        </thead>
        <tbody>
          {poule.classement.map((ligne) => (
            <tr key={ligne.archer_id}>
              <td>
                {ligne.rang}
                {ligne.ex_aequo ? ' =' : ''}
              </td>
              <td>{nom(ligne.archer_id)}</td>
              <td>{ligne.points_match}</td>
              <td>{ligne.diff_sets}</td>
              <td>{ligne.diff_score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

/** Les rangs que les cinq critères n'ont pas séparés, dédoublonnés et ordonnés.
 *
 * Sert à **nommer** le rang dans l'alerte : l'annonce du barrage se fait au panneau admin (elle est
 * derrière `exiger_admin`, donc hors de portée de cet écran scoreur), et l'organisateur doit y
 * ressaisir le rang disputé. Le lui faire lire ici évite de le lui faire deviner — c'est ce champ
 * qui décide si le verdict refermera le classement ou ne fera rien.
 */
function rangsExAequo(poule: Poule): number[] {
  return [...new Set(poule.classement.filter((l) => l.ex_aequo).map((l) => l.rang))].sort(
    (a, b) => a - b,
  )
}
