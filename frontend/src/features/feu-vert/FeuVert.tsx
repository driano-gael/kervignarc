// Écran de pilotage « Feu vert — lancer le tour » (E12US002, ADR-0056) — surface de l'organisateur.
//
// « Ne jamais découvrir un blocage en appuyant sur le bouton » : l'écran montre **en continu** ce
// qui est prêt et ce qui bloque, nommé (« en attente du duel n°2 », « cible non attribuée ») — il
// n'empêche rien (`P-3`). Le bouton **chiffre** ce qu'il déclenche et, à l'appui, fait partir les
// duels prêts ; le serveur émet alors un signal diffusé aux postes et écrans
// (E04US018/E07US008/E07US004). Live par poll court.

import { useState } from 'react'
import { BoutonConfirme } from '../../shared/ui/BoutonConfirme'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { ChoixCreneau } from '../departs/ChoixCreneau'
import { useCreneauDesDuels } from '../departs/hooks'
import { useAvancementPhases } from '../phases/hooks'
import type { DuelAVenir } from './api'
import {
  actionDuel,
  afficheDuel,
  archersForfaitables,
  libelleBouton,
  libelleCibles,
  nomDuelliste,
  type ActionLigne,
} from './etat'
import {
  useDeclarerForfaitDepuisFeuVert,
  useFeuVert,
  useImpactLancement,
  useLancerTour,
} from './hooks'

// `surPlanDeDuels` vient de la **coquille** : la navigation entre écrans d'administration lui
// appartient (`CoquilleAdmin.allerA`), une feature ne construit pas de chemin elle-même.
export function FeuVert({
  tournoiId,
  surPlanDeDuels,
}: {
  tournoiId: number
  surPlanDeDuels: () => void
}) {
  // Créneau **figé une fois résolu** (cf. `useCreneauDesDuels`) : le pilotage du tour ne doit pas
  // changer de créneau tout seul parce qu'une qualification vient de se clore ailleurs.
  const { departs, liste, departId, choisir } = useCreneauDesDuels(tournoiId)
  // ⚠️ **`useAvancementPhases(departId)` et non `usePhases(tournoiId)`** (revue E01US025, axe
  // adversarial). Depuis ADR-0076, `GET /tournois/{id}/phases` rend le **déroulé** — des `id` de
  // `deroule_etape` —, alors que « lancer le tour » s'adresse à une **phase**, l'avancement d'une
  // étape dans un créneau. Les deux tables ont des séquences d'`id` indépendantes : sur un tournoi
  // mono-départ elles coïncident une à une, si bien que l'erreur était invisible ; sur deux
  // créneaux, l'organisateur de l'après-midi lançait le tour du **matin**, sans la moindre erreur.
  const phases = useAvancementPhases(departId)
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

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Feu vert — lancer le tour</h2>

      {/* Le créneau commande tout l'écran : on lance le tour d'**un** départ (ADR-0075). Le défaut
          est celui **dont on joue les duels** (`creneauDesDuels`) — et non celui de l'écran de
          salle, qui désignerait le créneau suivant dès la qualification close. */}
      <ChoixCreneau departs={liste} valeur={departId} surChangement={choisir} />
      {departs.isSuccess && liste.length === 0 && (
        <p className="carte__etat">Aucun départ n’est encore défini pour ce tournoi.</p>
      )}

      {departId !== null && phases.isPending && <p className="carte__etat">Chargement…</p>}
      {departId !== null && !phases.isPending && tableaux.length === 0 && (
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
      {/* DETTE-050 : rendu ad hoc non rallié à `shared/ui/texteErreur` — `error.message` brut.
          Écran du jour J : c'est précisément là qu'une coupure LAN est probable. */}
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
                <LigneDuel
                  key={duel.numero}
                  duel={duel}
                  duels={feu.data.duels}
                  tournoiId={tournoiId}
                  phaseId={phaseId}
                  surPlanDeDuels={surPlanDeDuels}
                />
              ))}
            </ul>
          )}

          <div className="feu-vert__actions">
            {/* Le geste le plus lourd du jour J : il prévient les postes et les écrans. La question
                **redit ce qui part** au lieu du « OK / Annuler » d'un `confirm` natif (A15 : *« une
                pop-up propre et bien design »*), et le bouton de confirmation porte le même libellé
                que le déclencheur — c'est le même geste, le renommer ferait douter. */}
            <BoutonConfirme
              libelle={libelle ?? 'Aucun duel prêt à lancer'}
              disabled={libelle === null || lancer.isPending}
              enCours={lancer.isPending}
              titre="Lancer le tour ?"
              message="Les postes de cible et les écrans de salle sont prévenus immédiatement."
              detail={impact.data === undefined ? null : (libelleBouton(impact.data) ?? null)}
              libelleConfirmer="Lancer le tour"
              onConfirmer={() => lancer.mutate()}
            />
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

function LigneDuel({
  duel,
  duels,
  tournoiId,
  phaseId,
  surPlanDeDuels,
}: {
  duel: DuelAVenir
  duels: DuelAVenir[]
  tournoiId: number
  phaseId: number | null
  surPlanDeDuels: () => void
}) {
  const { classe, libelle } = afficheDuel(duel)
  const cibles = libelleCibles(duel)
  const action = actionDuel(duel, duels)
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
      {action && (
        <ActionLevee
          action={action}
          numeroLigne={duel.numero}
          tournoiId={tournoiId}
          phaseId={phaseId}
          surPlanDeDuels={surPlanDeDuels}
        />
      )}
    </li>
  )
}

// L'action qui **lève** le manquement de la ligne (CA E16US008). Trois formes, une par manquement
// que le serveur sait nommer : un renvoi au plan de duels, un dépliage du duel amont, ou l'aveu
// qu'aucun geste ne débloque d'ici — mieux qu'un bouton qui n'aboutirait pas.
function ActionLevee({
  action,
  numeroLigne,
  tournoiId,
  phaseId,
  surPlanDeDuels,
}: {
  action: ActionLigne
  numeroLigne: number
  tournoiId: number
  phaseId: number | null
  surPlanDeDuels: () => void
}) {
  const [deplie, setDeplie] = useState(false)
  // ⚠️ Une mutation **par ligne**, pas une pour l'écran : partagée, un forfait en cours grisait les
  // boutons de toutes les autres lignes et son erreur s'affichait sous chacune.
  const forfait = useDeclarerForfaitDepuisFeuVert(tournoiId, phaseId)

  if (action.genre === 'placement') {
    return (
      <div className="feu-vert__levee">
        <button type="button" className="bouton--discret" onClick={surPlanDeDuels}>
          Attribuer une cible — ouvrir le plan de duels
        </button>
      </div>
    )
  }
  if (action.genre === 'sans-recours') {
    return <p className="feu-vert__levee feu-vert__levee--inerte">{action.explication}</p>
  }

  const forfaitables = archersForfaitables(action.sources)
  return (
    <div className="feu-vert__levee">
      <button
        type="button"
        className="bouton--discret"
        aria-expanded={deplie}
        aria-controls={`feu-vert-sources-${numeroLigne}`}
        onClick={() => setDeplie((ouvert) => !ouvert)}
      >
        {deplie ? 'Masquer le duel qui bloque' : 'Voir le duel qui bloque'}
      </button>
      {deplie && (
        <>
          <ul className="feu-vert__sources" id={`feu-vert-sources-${numeroLigne}`}>
            {action.sources.map((source) => (
              <li key={source.numero}>
                Duel n°{source.numero} · {source.detail}
              </li>
            ))}
          </ul>
          {forfaitables.map((archer) => (
            <BoutonConfirme
              key={archer.archer_id}
              className="bouton--danger"
              libelle={`Déclarer ${archer.libelle} forfait`}
              disabled={forfait.isPending}
              enCours={forfait.isPending}
              ton="danger"
              titre={`Déclarer ${archer.libelle} forfait ?`}
              message={`Son adversaire du duel n°${archer.numero_duel} passe d'office (walkover) : le tableau avance et ce duel-ci n'attend plus son issue.`}
              detail="Abandon. ⚠️ Aucun écran ne défait un forfait de duel aujourd'hui (DETTE-090) : à ne déclarer qu'en dernier recours."
              libelleConfirmer="Déclarer forfait"
              onConfirmer={() => forfait.mutate(archer.archer_id)}
            />
          ))}
          {forfait.isSuccess && (
            <p className="feu-vert__levee--inerte" role="status">
              Forfait enregistré — l’adversaire passe.
            </p>
          )}
          {forfait.isError && <MessageErreur erreur={forfait.error} />}
        </>
      )}
    </div>
  )
}
