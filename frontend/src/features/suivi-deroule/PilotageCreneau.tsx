// Pilotage du déroulé **dans un créneau** (E01US025, ADR-0076) — axe pilotage, poste admin.
//
// **Pourquoi ce panneau existe.** Jusqu'à ADR-0076, l'écran « Phases » portait les deux mailles :
// on y composait la séquence *et* on la faisait vivre, parce qu'un tournoi n'avait qu'une suite de
// phases. Depuis, le déroulé est défini **une fois** au tournoi et chaque départ le rejoue : « la
// phase 2 » ne désigne plus un objet mais N avancements, un par créneau. Un bouton « Démarrer »
// sur le déroulé n'aurait donc plus de destinataire — démarrer *où* ? Le geste descend ici, à la
// maille qui a un statut, et l'écran « Phases » redevient un atelier de composition.
//
// **Pourquoi ici et pas dans un écran neuf.** « Suivi du déroulé » est déjà la destination de l'axe
// pilotage : l'organisateur y lit où en est son tournoi. Lui faire changer d'écran pour agir sur ce
// qu'il vient de lire serait une couture inutile. Le schéma reste la vue d'ensemble du tournoi ; ce
// panneau est la commande, créneau par créneau.
//
// ⚠️ Ce module n'est **pas** monté sur l'écran de salle (`EcranSalle` compose sa propre vue à partir
// des mêmes hooks) : « aucune interaction » y reste vrai, CA E07US004.

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { LIBELLE_TYPE } from '../../shared/phases/catalogue'
import type { Phase, StatutPhase, TransitionPhase } from '../phases/api'
import { useAvancementPhases, useChangerStatutPhase } from '../phases/hooks'
import { useArretsEnAttente, useRelancerArret } from './hooks'

const LIBELLE_STATUT: Record<StatutPhase, string> = {
  a_venir: 'À venir',
  en_cours: 'En cours',
  en_pause: 'En pause',
  terminee: 'Terminée',
}

// Transitions offertes selon le statut courant (ADR-0045 §1). Le serveur reste l'autorité (409 si
// l'état a changé entre l'affichage et le clic) — cette table ne fait qu'éviter d'offrir un geste
// dont on sait déjà qu'il sera refusé.
const TRANSITIONS: Record<StatutPhase, { transition: TransitionPhase; libelle: string }[]> = {
  a_venir: [{ transition: 'demarrer', libelle: 'Démarrer' }],
  en_cours: [
    { transition: 'mettre_en_pause', libelle: 'Mettre en pause' },
    { transition: 'terminer', libelle: 'Terminer' },
  ],
  en_pause: [{ transition: 'reprendre', libelle: 'Reprendre' }],
  terminee: [],
}

/** ⚠️ Le créneau est **reçu**, plus choisi ici (E01US025). Le sélecteur a été hissé dans
 * `SuiviDeroule` : le schéma au-dessus est lui aussi celui d’un créneau depuis ADR-0075, et deux
 * sélecteurs sur le même écran laisseraient lire l’avancement du matin sous le dessin de
 * l’après-midi. Un écran, un créneau. */
export function PilotageCreneau({
  tournoiId,
  departId,
  aucunCreneau,
}: {
  tournoiId: number
  departId: number | null
  aucunCreneau: boolean
}) {
  const phases = useAvancementPhases(departId)

  return (
    <section className="carte">
      <h3 className="carte__soustitre">Piloter un créneau</h3>
      <p className="carte__aide">
        Le déroulé est commun au tournoi ; son <strong>avancement</strong> appartient à chaque
        créneau. Le départ du matin peut être en duels pendant que celui de l’après-midi qualifie.
      </p>
      {aucunCreneau && (
        <p className="carte__etat">
          Aucun départ n’est encore défini pour ce tournoi : il n’y a rien à piloter.
        </p>
      )}
      <MessageErreur erreur={phases.error} />
      {/* E05US033 — la relance des pauses, **avant** la liste des phases : quand la salle attend, c'est
          le seul geste qui compte, et le faire chercher au milieu d'une liste de six phases est
          exactement le piège du CA (« en oublier une »). */}
      {departId !== null && <RelanceDesArrets departId={departId} />}
      {departId !== null && phases.isPending && <p className="carte__etat">Chargement…</p>}
      {phases.data?.length === 0 && (
        <p className="carte__etat">
          Ce créneau ne joue encore aucune phase : composez le déroulé depuis « Phases ».
        </p>
      )}
      {phases.data !== undefined && phases.data.length > 0 && departId !== null && (
        <ol className="liste-phases">
          {phases.data.map((phase) => (
            <LignePilotage key={phase.id} tournoiId={tournoiId} departId={departId} phase={phase} />
          ))}
        </ol>
      )}
    </section>
  )
}

function LignePilotage({
  tournoiId,
  departId,
  phase,
}: {
  tournoiId: number
  departId: number
  phase: Phase
}) {
  const changerStatut = useChangerStatutPhase(tournoiId, departId)

  return (
    <li className="phase">
      <div className="phase__ligne">
        <span className="phase__ordre">{phase.ordre}</span>
        <span className="phase__type">{LIBELLE_TYPE[phase.type]}</span>
        <span className={`badge badge--${phase.statut.replace('_', '-')}`}>
          {LIBELLE_STATUT[phase.statut]}
        </span>
      </div>
      <div className="phase__actions">
        {TRANSITIONS[phase.statut].map((action) => (
          <button
            key={action.transition}
            type="button"
            className="bouton--discret"
            disabled={changerStatut.isPending}
            onClick={() =>
              changerStatut.mutate({ phaseId: phase.id, transition: action.transition })
            }
          >
            {action.libelle}
          </button>
        ))}
      </div>
      <MessageErreur erreur={changerStatut.error} />
    </li>
  )
}

/**
 * Les pauses atteintes qui attendent un geste (E05US033, ADR-0091).
 *
 * ⚠️ **Un bouton par arrêt, pas par phase**, et c'est un CA : un arrêt de portée « créneau » a pu
 * mettre quatre phases en pause, et « quatre boutons pour un seul arrêt créerait exactement le piège
 * qu'on cherche à éviter — en oublier une ». Le compte des phases concernées est donc affiché, mais
 * la commande reste unique.
 *
 * ⚠️ **Ne rend rien quand il n'y a rien à relancer**, plutôt qu'un « aucune pause en attente »
 * permanent. Le panneau de pilotage sert tous les jours ; une ligne vide qui ne bouge jamais cesse
 * d'être lue, et c'est précisément celle qu'on veut voir le jour où elle apparaît.
 */
function RelanceDesArrets({ departId }: { departId: number }) {
  const arrets = useArretsEnAttente(departId)
  const relancer = useRelancerArret(departId)

  if (arrets.data === undefined || arrets.data.length === 0) {
    return <MessageErreur erreur={arrets.error} />
  }

  return (
    <div className="carte__etat carte__etat--alerte" role="status">
      <p>
        <strong>
          {arrets.data.length === 1
            ? 'Une pause programmée attend votre relance.'
            : `${arrets.data.length} pauses programmées attendent votre relance.`}
        </strong>{' '}
        Le tir est suspendu&nbsp;: les archers concernés lisent «&nbsp;en attente&nbsp;».
      </p>
      <ul className="deroule__liste">
        {arrets.data.map((arret) => (
          <li key={arret.id}>
            <span>
              Pause après le tour {arret.apres_tour}
              {arret.portee === 'depart'
                ? ` — tout le créneau (${arret.phases_arretees.length} phase${
                    arret.phases_arretees.length > 1 ? 's' : ''
                  })`
                : ' — cette phase seule'}
            </span>
            <button
              type="button"
              className="bouton"
              disabled={relancer.isPending}
              onClick={() => relancer.mutate(arret.id)}
            >
              Relancer
            </button>
          </li>
        ))}
      </ul>
      <MessageErreur erreur={relancer.error} />
    </div>
  )
}
