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

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { ChoixCreneau } from '../departs/ChoixCreneau'
import { useDeparts } from '../departs/hooks'
import { LIBELLE_TYPE } from '../../shared/phases/catalogue'
import type { Phase, StatutPhase, TransitionPhase } from '../phases/api'
import { useAvancementPhases, useChangerStatutPhase } from '../phases/hooks'
import { departDeSalle } from '../salle/rotation'

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

export function PilotageCreneau({ tournoiId }: { tournoiId: number }) {
  const [choixDepart, setChoixDepart] = useState<number | null>(null)
  const departs = useDeparts(tournoiId)
  const liste = departs.data ?? []
  // Défaut : le créneau qu'on est en train de tirer — le même choix que le plan de cibles et le
  // classement de salle, par le même helper pur (`salle/rotation.ts`). Retomber sur `departs[0]`
  // proposerait de piloter le départ du matin, clos depuis des heures.
  const departId = choixDepart ?? departDeSalle(liste)?.id ?? null
  const phases = useAvancementPhases(departId)

  return (
    <section className="carte">
      <h3 className="carte__soustitre">Piloter un créneau</h3>
      <p className="carte__aide">
        Le déroulé est commun au tournoi ; son <strong>avancement</strong> appartient à chaque
        créneau. Le départ du matin peut être en duels pendant que celui de l’après-midi qualifie.
      </p>
      {departs.isSuccess && liste.length === 0 && (
        <p className="carte__etat">
          Aucun départ n’est encore défini pour ce tournoi : il n’y a rien à piloter.
        </p>
      )}
      <ChoixCreneau departs={liste} valeur={departId} surChangement={setChoixDepart} />
      <MessageErreur erreur={phases.error} />
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
