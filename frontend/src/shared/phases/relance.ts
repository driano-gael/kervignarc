// Ce que l'application **dit** d'une salle qui attend sa relance. Décision : ADR-0092.
//
// ⚠️ **Module à part, et non trois lignes dans le composant** : `react-refresh` interdit à un
// module de rendu d'exporter aussi des fonctions. ⚠️ **Le serveur rend un instant, ce module en
// fait une durée** — le calcul ne peut pas remonter côté serveur : la route est pollée toutes les
// 10 s, mais le rendu vit *entre* deux réponses, si bien qu'un « depuis 14 min » y resterait à 14.

import { nommerType, TYPES_ARRETABLES } from './catalogue'
import type { TypePhase } from './catalogue'
import type { StatutPhase } from '../schema-braquets/modele'

/** La forme minimale dont ce module a besoin — un sous-ensemble d'`ArretEnAttente`.
 *
 * Volontairement pauvre : ni portée, ni phase déclenchante. Le typer sur `ArretEnAttente`
 * ferait dépendre `shared/` d'une feature, ce que le sens des imports interdit. */
export interface ArretQuiAttend {
  phases_arretees: number[]
  /** Instant ISO 8601 (UTC) de la **première** extinction, ou `null` si rien n'est encore éteint. */
  arrete_depuis: string | null
}

export interface ResumeDeRelance {
  /** Combien de phases sont éteintes en tout, **sans doublon** entre arrêts. */
  nbPhases: number
  /** Depuis combien de minutes la **plus ancienne** attend, ou `null` si aucune n'est datée. */
  minutes: number | null
}

/** Ce qui attend une relance dans un créneau — ou `null` s'il n'y a rien à annoncer.
 *
 * ⚠️ **Compte les phases, pas les arrêts** (lettre du CA) : un arrêt de portée « créneau » peut en
 * avoir éteint quatre d'un coup. ⚠️ **Sans doublon** : deux arrêts peuvent nommer la même phase, et
 * annoncer « 3 phases » sur une salle qui en compte deux est faux dans le sens qui **alarme**. ⚠️
 * **La durée est celle de la plus ancienne** — c'est le chiffre qui décide ; un arrêt non daté ne
 * participe pas au calcul mais ne l'annule pas.
 */
export function resumeDeRelance(
  arrets: readonly ArretQuiAttend[],
  maintenant: number,
): ResumeDeRelance | null {
  const phases = new Set<number>()
  let plusAncien: number | null = null
  for (const arret of arrets) {
    for (const phase of arret.phases_arretees) phases.add(phase)
    if (arret.arrete_depuis === null) continue
    const instant = Date.parse(arret.arrete_depuis)
    // Une date illisible est ignorée plutôt que rendue `NaN` : le compteur est un confort, il ne
    // doit jamais empêcher la phrase — c'est elle qui porte le CA.
    if (Number.isNaN(instant)) continue
    if (plusAncien === null || instant < plusAncien) plusAncien = instant
  }
  if (phases.size === 0) return null
  return {
    nbPhases: phases.size,
    // `max(0, …)` : une horloge client en avance sur le serveur donnerait un « depuis -1 min ».
    // L'écart est de quelques secondes sur un réseau local, donc le plancher se lit « à l'instant ».
    minutes:
      plusAncien === null ? null : Math.max(0, Math.floor((maintenant - plusAncien) / 60000)),
  }
}

/**
 * La phrase de la pastille, telle que le CA la formule.
 *
 * Le « depuis » est **omis** quand rien n'est daté plutôt que remplacé par un zéro : un compteur
 * inventé est pire qu'un compteur absent — il fait croire que la salle vient de s'arrêter.
 */
export function phraseDeRelance(resume: ResumeDeRelance): string {
  const sujet =
    resume.nbPhases === 1
      ? 'Une phase attend votre relance'
      : `${resume.nbPhases} phases attendent votre relance`
  if (resume.minutes === null) return `${sujet}.`
  if (resume.minutes < 1) return `${sujet} — à l’instant.`
  return `${sujet} depuis ${resume.minutes} min.`
}

/** Ce qu'il faut savoir d'une phase pour décider si on peut y poser une pause. Sous-ensemble de
 * `Phase` + `AvancementBloc`, pour que `shared/` ne dépende d'aucune feature.
 *
 * `statut` est typé `StatutPhase` — déclaré dans `shared/`, donc sans créer la dépendance que ce
 * module évite. Le laisser en `string` (première écriture) faisait compiler `'en-cours'` avec un
 * tiret : la fonction aurait rendu `false` en silence et le formulaire aurait disparu sans un
 * signe (revue E05US034). */
export interface PhasePosable {
  statut: StatutPhase
  type: TypePhase
  tourCourant: number | null
  nbTours: number
}

/** Peut-on proposer « bloquer dans x tours » sur cette phase ? (CA E05US034)
 *
 * ⚠️ **Extraite du JSX parce que c'est une règle, pas de la mise en page** — dans une condition JSX
 * elle serait invisible au test. Quatre conditions, chacune miroir d'un refus serveur : phase **en
 * cours** ; type qui **annonce ses tours** (`TYPES_ARRETABLES`, ADR-0093) ; **tour courant
 * lisible** ; **un tour restant après celui qui tourne** (au dernier, le serveur refuse toujours).
 * ⚠️ `nbTours <= 1` = non posable : signature du repli d'`avancement_bloc`.
 */
export function peutPoserUnePause(phase: PhasePosable): boolean {
  return (
    phase.statut === 'en_cours' &&
    TYPES_ARRETABLES.has(phase.type) &&
    phase.tourCourant !== null &&
    phase.nbTours > 1 &&
    phase.tourCourant < phase.nbTours
  )
}

/** Ce qu'il faut savoir d'une phase pour dire où en est son tour. Sous-ensemble d'`AvancementBloc`,
 * même raison que `PhasePosable` : `shared/` ne dépend d'aucune feature. */
export interface TourLisible {
  tour_courant: number | null
  nb_tours: number
  libelle_tour_courant: string | null
}

/** « Ronde 3 — tour 3 sur 5 » : le tour en cours, **lisible en tant que tel** (CA E05US034).
 *
 * ⚠️ **Le repli n'est pas mort** (rectifié en 2ᵉ passe) : `libelle_de_tour` rend `null` pour toute
 * unité `PHASE_ENTIERE`, pas seulement quand `tour_courant` l'est. Le cas est inatteignable
 * aujourd'hui (`nbTours <= 1` l'écarte plus haut) mais supprimer le repli sur cette hypothèse
 * ferait disparaître la ligne en silence. `libelle_tour_courant` est **servi par le serveur**,
 * jamais recomposé : la règle « à rebours de la finale » a déjà deux domiciles (`DETTE-020`).
 */
export function libelleEtatDuTour(avancement: TourLisible | null): string | null {
  if (avancement === null || avancement.tour_courant === null) return null
  if (avancement.nb_tours <= 1) return null
  const position = `tour ${avancement.tour_courant} sur ${avancement.nb_tours}`
  if (avancement.libelle_tour_courant === null) return position
  return `${avancement.libelle_tour_courant} — ${position}`
}

/** Ce qu'il faut savoir d'une phase pour décider ce que la salle doit lire. */
export interface PhaseAffichable {
  statut: StatutPhase
  type: TypePhase
}

/** Ce que l'**écran de salle** doit annoncer d'une pause — ou rien du tout (CA E05US034).
 *
 * ⚠️ **Née d'un bloquant de 2ᵉ passe** : annoncer « le tir est suspendu » dès qu'**une** phase du
 * créneau est en pause faisait annoncer au gymnase entier une suspension générale pendant que le
 * tableau d'à côté tirait — sur une surface collective, une annonce non qualifiée arrête des gens
 * que ça ne concerne pas. Trois réponses : `null` (aucune phase en pause, on se tait), `[]` (plus
 * rien ne tire, la phrase générale est vraie), une liste (on **nomme** ce qui est suspendu).
 */
export function phasesSuspendues(phases: readonly PhaseAffichable[]): string[] | null {
  const enPause = phases.filter((phase) => phase.statut === 'en_pause')
  if (enPause.length === 0) return null
  const tireEncore = phases.some((phase) => phase.statut === 'en_cours')
  if (!tireEncore) return []
  return enPause.map((phase) => nommerType(phase.type))
}

/** Combien de tours on peut encore « bloquer d'avance » sur cette phase (CA E05US034).
 *
 * ⚠️ **Extraite pour être tenue en vis-à-vis du refus serveur** : celui-ci pose `apres_tour =
 * tour_courant + x - 1` et refuse `>= nb_tours`, donc la borne du champ vaut exactement `nb_tours -
 * tour_courant`. Écrite en dur dans le JSX, cette coïncidence n'avait aucun oracle. N'a de sens que
 * sur une phase que `peutPoserUnePause` accepte.
 */
export function toursBloquablesRestants(phase: PhasePosable): number {
  if (phase.tourCourant === null) return 0
  return Math.max(0, phase.nbTours - phase.tourCourant)
}
