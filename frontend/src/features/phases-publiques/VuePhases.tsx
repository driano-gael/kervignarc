// L'onglet public « Rencontres » (E05US031, ADR-0089) — et la vue `tableaux` de l'écran de salle.
//
// **Ce composant remplace `VueTableaux` comme point d'entrée public.** Jusqu'à cette US, l'onglet
// était bâti sur `/tableaux/departs/{id}`, qui ne rend qu'un **arbre de duels** : dès que le tournoi
// passait en poules, en système suisse ou en Big Shoot Off, le spectateur n'avait plus rien. L'index
// est donc désormais la **liste d'avancement du créneau** (ADR-0089 §4) — un arbre est un cas
// particulier de phase, pas le sommaire.
//
// ⚠️ **C'est un orchestrateur, et il assume d'importer ses formats.** La règle du front n'est pas
// « aucune feature n'importe d'une feature » mais « le **vocabulaire partagé** vit dans `shared/` » —
// distinction posée en revue d'E05US030 dans l'en-tête de `shared/salle/place.ts`, et déjà exercée
// par `features/phases`, qui orchestre les mêmes formats côté organisateur. Ce qui est monté en
// `shared/` ici, c'est le **modèle de rendu** (`shared/rencontres/`), pas les surfaces.
//
// ⚠️ **Aucun store lu.** `mode` et `suivis` descendent en props : ce composant sert aussi l'écran de
// salle, où il n'y a personne à suivre (correctif de revue d'E16US004, à ne pas refaire).

import { useState, type ReactNode } from 'react'

import { ErreurApi } from '../../shared/api/client'
import { nommerType } from '../../shared/phases/catalogue'
import { type ModeAffichage } from '../../shared/suivis/focus'
import { VueRencontres } from '../../shared/rencontres/VueRencontres'
import { useDeparts } from '../departs/hooks'
import { departDeSalle } from '../salle/rotation'
import { VueTableaux } from '../tableaux/VueTableaux'
import { VueBigShootOffPublique } from '../big-shoot-off/VueBigShootOffPublique'
import { useEtatBigShootOffPublic } from '../big-shoot-off/hooks'
import { useEtatPoules } from '../poules/hooks'
import { formatPublicDesPoules } from '../poules/publique'
import { useEtatSuisse } from '../suisse/hooks'
import { formatPublicDuSuisse } from '../suisse/publique'
import type { PhasePublique } from './api'
import { usePhasesPubliques } from './hooks'
import { libelleStatut, phaseAffichee, renduDe } from './presentation'

export function VuePhases({
  tournoiId,
  interactif = true,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  interactif?: boolean
  mode?: ModeAffichage
  suivis?: number[]
}) {
  const [phaseChoisie, setPhaseChoisie] = useState<number | null>(null)
  // **Les phases appartiennent à un créneau** (E01US025, ADR-0075). Ni l'écran de salle ni l'appli
  // publique n'ont de sélecteur de départ ici : on prend le créneau **qu'on est en train de tirer**,
  // par le même helper pur que le classement, le plan de cibles et l'arbre.
  const departs = useDeparts(tournoiId)
  const departId = departDeSalle(departs.data ?? [])?.id ?? null
  const phases = usePhasesPubliques(departId)

  if (departs.isSuccess && (departs.data ?? []).length === 0) {
    return <p className="carte__etat">Aucun départ n’est encore défini pour ce tournoi.</p>
  }
  // Les **données priment sur l'erreur** : React Query garde le `data` de la dernière lecture
  // réussie pendant un échec. Tester `isError` d'abord jetterait une liste encore exacte au premier
  // clignotement réseau et laisserait l'écran projeté sur un message d'erreur ≥ 20 s — le défaut
  // qu'E07US008 a dû corriger en revue, à ne pas refaire ici.
  if (phases.data === undefined) {
    return (
      <p className="carte__etat">
        {phases.isError ? 'Connexion momentanément perdue — mise à jour au retour.' : 'Chargement…'}
      </p>
    )
  }

  const phase = phaseAffichee(phases.data, interactif ? phaseChoisie : null)
  if (phase === null) {
    // Ni erreur ni page blanche : le matin, le déroulé peut n'être pas encore composé.
    return <p className="carte__etat">Le déroulé de ce départ n’est pas encore composé.</p>
  }

  return (
    <div className="tableaux">
      {interactif && phases.data.length > 1 && (
        <div className="tableaux__barre">
          <label className="tableaux__phase">
            <span className="tableaux__phase-libelle">Phase</span>
            <select value={phase.id} onChange={(e) => setPhaseChoisie(Number(e.target.value))}>
              {/* **Toutes** les phases du créneau, terminées comprises : c'est ce qui rend le
                  classement d'une poule close consultable après le démarrage de la suivante (CA du
                  cadrage du 17/08/2026), sans une ligne de backend. L'`ordre` est affiché parce que
                  deux phases peuvent porter le même type — « Poules » deux fois de suite est une
                  cascade banale, et sans le rang la liste n'a plus de référent. */}
              {[...phases.data]
                .sort((a, b) => a.ordre - b.ordre)
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.ordre}. {nommerType(p.type)} — {libelleStatut(p.statut)}
                  </option>
                ))}
            </select>
          </label>
        </div>
      )}

      <p className="tableaux__entete">
        {nommerType(phase.type)} · {libelleStatut(phase.statut)}
      </p>

      <ContenuDePhase
        tournoiId={tournoiId}
        phase={phase}
        interactif={interactif}
        mode={mode}
        suivis={suivis}
      />
    </div>
  )
}

/** Le routage par type — le cœur de l'US (ADR-0089 §1). */
function ContenuDePhase({
  tournoiId,
  phase,
  interactif,
  mode,
  suivis,
}: {
  tournoiId: number
  phase: PhasePublique
  interactif: boolean
  mode: ModeAffichage
  suivis: number[]
}) {
  const rendu = renduDe(phase.type)
  if (rendu === 'tableau') {
    // L'arbre garde sa vue, inchangée. On lui **impose** la phase choisie ici : sans cela, deux
    // sélecteurs coexisteraient et diraient des choses différentes sur le même écran.
    return (
      <VueTableaux
        tournoiId={tournoiId}
        phaseId={phase.id}
        interactif={interactif}
        mode={mode}
        suivis={suivis}
      />
    )
  }
  if (rendu === 'poules') {
    return (
      <PhasePoules
        tournoiId={tournoiId}
        phase={phase}
        interactif={interactif}
        mode={mode}
        suivis={suivis}
      />
    )
  }
  if (rendu === 'suisse') {
    return (
      <PhaseSuisse
        tournoiId={tournoiId}
        phase={phase}
        interactif={interactif}
        mode={mode}
        suivis={suivis}
      />
    )
  }
  if (rendu === 'big_shoot_off') {
    return (
      <PhaseBigShootOff
        tournoiId={tournoiId}
        phase={phase}
        interactif={interactif}
        mode={mode}
        suivis={suivis}
      />
    )
  }
  // ⚠️ **On nomme où la lecture se trouve, on ne laisse pas un blanc.** Une qualification a bien une
  // vue publique — l'onglet « Classement » — et un échauffement ne produit rien par définition
  // (§10.1). Renvoyer un écran vide ferait chercher une panne dans les deux cas.
  return <PhaseSansVue phase={phase} interactif={interactif} />
}

/** Le squelette commun aux trois lectures de format : chargement, refus déterministe, panne.
 *
 * ⚠️ Un **409** est la réponse normale d'une phase non réglée (« ce Big Shoot Off n'a pas de liste
 * de sortants »), pas une panne : les hooks ne le réessaient donc pas, et l'écran le dit comme un
 * état et non comme une erreur.
 *
 * ⚠️ **Une panne n'est pas un refus, et les confondre fait mentir l'écran.** La première rédaction
 * prenait un booléen `isError` : un 500, une coupure Wi-Fi ou un redémarrage serveur affichaient
 * « cette phase n'est pas encore prête » **pendant qu'elle se jouait**. Et c'était durable — les
 * hooks ne réessaient pas, et une reconnexion WebSocket ne réinvalide rien tant qu'aucune écriture
 * ne survient ailleurs. Le composant parent, cent lignes plus haut, tenait déjà le raisonnement
 * inverse (correctif de revue d'E07US008) : le trou avait seulement été déplacé.
 */
function EtatDeLecture({
  chargement,
  erreur,
  children,
}: {
  chargement: boolean
  erreur: unknown
  children: ReactNode
}) {
  if (chargement) return <p className="carte__etat">Chargement…</p>
  if (erreur !== null && erreur !== undefined) {
    // Un statut déterministe (la phase n'est pas réglée, elle n'existe pas encore) se dit comme un
    // état ; tout le reste — pas de statut du tout, ou 5xx — est une panne de liaison.
    const refus =
      erreur instanceof ErreurApi && [404, 409, 422].includes(erreur.statut)
        ? 'Cette phase n’est pas encore prête à être suivie — elle sera visible dès qu’elle sera réglée et lancée.'
        : 'Connexion momentanément perdue — mise à jour au retour.'
    return <p className="carte__etat">{refus}</p>
  }
  return <>{children}</>
}

function PhasePoules({
  tournoiId,
  phase,
  interactif,
  mode,
  suivis,
}: {
  tournoiId: number
  phase: PhasePublique
  interactif: boolean
  mode: ModeAffichage
  suivis: number[]
}) {
  const etat = useEtatPoules(tournoiId, phase.id)
  return (
    <EtatDeLecture
      chargement={etat.data === undefined && !etat.isError}
      erreur={etat.data === undefined ? etat.error : null}
    >
      {etat.data !== undefined && (
        <VueRencontres
          format={formatPublicDesPoules(etat.data)}
          interactif={interactif}
          mode={mode}
          suivis={suivis}
        />
      )}
    </EtatDeLecture>
  )
}

function PhaseSuisse({
  tournoiId,
  phase,
  interactif,
  mode,
  suivis,
}: {
  tournoiId: number
  phase: PhasePublique
  interactif: boolean
  mode: ModeAffichage
  suivis: number[]
}) {
  const etat = useEtatSuisse(tournoiId, phase.id)
  return (
    <EtatDeLecture
      chargement={etat.data === undefined && !etat.isError}
      erreur={etat.data === undefined ? etat.error : null}
    >
      {etat.data !== undefined && (
        <VueRencontres
          format={formatPublicDuSuisse(etat.data)}
          interactif={interactif}
          mode={mode}
          suivis={suivis}
        />
      )}
    </EtatDeLecture>
  )
}

function PhaseBigShootOff({
  tournoiId,
  phase,
  interactif,
  mode,
  suivis,
}: {
  tournoiId: number
  phase: PhasePublique
  interactif: boolean
  mode: ModeAffichage
  suivis: number[]
}) {
  const etat = useEtatBigShootOffPublic(tournoiId, phase.id)
  return (
    <EtatDeLecture
      chargement={etat.data === undefined && !etat.isError}
      erreur={etat.data === undefined ? etat.error : null}
    >
      {etat.data !== undefined && (
        <VueBigShootOffPublique
          etat={etat.data}
          interactif={interactif}
          mode={mode}
          suivis={suivis}
        />
      )}
    </EtatDeLecture>
  )
}

/** Ce qu'on dit d'une phase qui n'a pas de vue ici — sans jamais laisser un blanc.
 *
 * ⚠️ **`interactif` change la formulation, pas seulement l'interaction.** Sur l'écran de salle il
 * n'y a ni onglet ni personne pour cliquer : renvoyer le spectateur vers « l'onglet Classement »
 * l'envoie sur une cible qui n'existe pas sur cet écran-là. On y nomme la **vue projetée**
 * correspondante. Le composant recevait déjà `interactif` deux niveaux plus haut sans le
 * descendre. */
function PhaseSansVue({ phase, interactif }: { phase: PhasePublique; interactif: boolean }) {
  if (phase.type === 'qualification') {
    return (
      <p className="carte__etat">
        {interactif
          ? 'Les résultats de la qualification se lisent dans l’onglet « Classement ».'
          : 'Les résultats de la qualification sont projetés par la vue « Classement ».'}
      </p>
    )
  }
  if (phase.type === 'echauffement') {
    return (
      <p className="carte__etat">
        L’échauffement ne produit ni point ni classement : il n’y a rien à suivre ici.
      </p>
    )
  }
  if (phase.type === 'barrage') {
    return (
      <p className="carte__etat">
        Ce barrage départage des ex æquo ; son résultat apparaît dans la phase qu’il alimente.
      </p>
    )
  }
  // Reste la **colline**, et tout type qu'un serveur plus récent nommerait. Le message ne promet
  // rien : dire « bientôt » serait un engagement que rien ici ne tient.
  return (
    <p className="carte__etat">
      {interactif
        ? 'Le détail de cette phase n’est pas encore consultable depuis l’application publique.'
        : 'Le détail de cette phase n’est pas encore projetable sur l’écran de salle.'}
    </p>
  )
}
