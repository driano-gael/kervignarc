// Écran de pilotage « Feu vert — lancer le tour » (E12US002, ADR-0056) — la surface de
// l'**organisateur** le jour J.
//
// « Ne jamais découvrir un blocage en appuyant sur le bouton. » L'écran montre **en continu** ce qui
// est prêt à partir et ce qui bloque (nommé : « en attente du duel n°2 », « cible non attribuée ») —
// il n'empêche rien (`P-3`), il montre. Le bouton **chiffre** ce qu'il déclenche (« N duels, cibles
// …, K archers ») et, à l'appui, fait **partir** les duels prêts : le serveur émet un signal diffusé
// aux postes/écrans (les récepteurs ciblés viendront avec E04US018/E07US008/E07US004). Live par poll
// court (les validations de duels d'un scoreur font avancer le tableau, cf. `hooks`).

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { usePhases } from '../phases/hooks'
import type { DuelAVenir } from './api'
import { afficheDuel, libelleBouton, libelleCibles, nomDuelliste } from './etat'
import { useFeuVert, useImpactLancement, useLancerTour } from './hooks'

export function FeuVert({ tournoiId }: { tournoiId: number }) {
  const phases = usePhases(tournoiId)
  // Le pilotage ne vaut que pour une phase de **tableau** : on ne propose que celles-là (jumeau du
  // sélecteur de la saisie en duels et du plan de duels). Le serveur reste l'autorité.
  const tableaux = (phases.data ?? []).filter((p) => p.type === 'elimination_directe')
  const [choisie, setChoisie] = useState<number | null>(null)
  // Si la phase choisie n'est plus une phase de tableau disponible (rare : suppression pendant le
  // pilotage), on retombe sur la première — plutôt que d'interroger une phase absente et de rester
  // bloqué sur « Feu vert injoignable » sans moyen d'en sortir.
  const phaseId =
    choisie !== null && tableaux.some((phase) => phase.id === choisie)
      ? choisie
      : (tableaux[0]?.id ?? null)

  const feu = useFeuVert(tournoiId, phaseId)
  const impact = useImpactLancement(tournoiId, phaseId)
  const lancer = useLancerTour(tournoiId, phaseId)

  const libelle = impact.data ? libelleBouton(impact.data) : null

  const demanderLancement = () => {
    if (libelle === null) return
    // Le bouton chiffre déjà l'impact ; la confirmation le redit pour éviter un lancement par
    // réflexe (le geste prévient les postes). Simple `confirm` en attendant une friction plus riche.
    if (window.confirm(`${libelle.replace('Lancer — ', 'Lancer ')} ?`)) lancer.mutate()
  }

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Feu vert — lancer le tour</h2>

      {phases.isPending && <p className="carte__etat">Chargement…</p>}
      {!phases.isPending && tableaux.length === 0 && (
        <p className="carte__etat">
          Aucune phase à élimination directe : définissez-en une dans «&nbsp;Phases&nbsp;».
        </p>
      )}

      {tableaux.length > 1 && (
        <label className="feu-vert__selecteur">
          Phase de tableau
          <select
            value={phaseId ?? ''}
            onChange={(evenement) => setChoisie(Number(evenement.target.value))}
          >
            {tableaux.map((phase) => (
              <option key={phase.id} value={phase.id}>
                Phase {phase.ordre}
              </option>
            ))}
          </select>
        </label>
      )}

      {phaseId !== null && feu.isPending && <p className="carte__etat">Chargement…</p>}
      {feu.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Feu vert injoignable — {feu.error.message}
        </p>
      )}

      {feu.data && (
        <>
          {feu.data.est_termine ? (
            <p className="carte__etat carte__etat--ok" role="status">
              Tableau terminé — plus rien à lancer.
            </p>
          ) : feu.data.duels.length === 0 ? (
            <p className="carte__etat">Aucun duel à venir.</p>
          ) : (
            <ul className="feu-vert__liste">
              {feu.data.duels.map((duel) => (
                <LigneDuel key={duel.numero} duel={duel} />
              ))}
            </ul>
          )}

          <div className="feu-vert__actions">
            <button
              type="button"
              disabled={libelle === null || lancer.isPending}
              onClick={demanderLancement}
            >
              {libelle ?? 'Aucun duel prêt à lancer'}
            </button>
            {lancer.isError && <MessageErreur erreur={lancer.error} />}
            {lancer.isSuccess && (
              <p className="carte__etat carte__etat--ok" role="status">
                Tour lancé — {lancer.data.nb_duels} duel(s) parti(s), les postes sont prévenus.
              </p>
            )}
          </div>
        </>
      )}
    </section>
  )
}

function LigneDuel({ duel }: { duel: DuelAVenir }) {
  const { classe, libelle } = afficheDuel(duel)
  const cibles = libelleCibles(duel)
  return (
    <li className="feu-vert__duel">
      <span className="feu-vert__match">
        Duel n°{duel.numero} <span className="feu-vert__tour">(tour {duel.tour})</span>
      </span>
      <span className="feu-vert__opposants">
        {nomDuelliste(duel.haut)} vs {nomDuelliste(duel.bas)}
      </span>
      <span className={`feu-vert__etat feu-vert__etat--${classe}`}>
        <span className="indicateur__pastille" aria-hidden="true" />
        {libelle}
        {classe === 'pret' && cibles ? ` · ${cibles}` : ''}
      </span>
    </li>
  )
}
