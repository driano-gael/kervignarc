// Ce que l'application **dit** d'une salle qui attend sa relance (E05US034, ADR-0092) — logique
// pure, aucun React.
//
// **Pourquoi un module à part et pas trois lignes dans le composant.** C'est le CA le plus important
// de l'US : sans ce rappel, la capacité livrée par E05US033 crée un **mode de panne neuf** — la
// salle attend, personne ne sait pourquoi, et rien n'a l'air anormal. Une phrase qui porte un CA se
// teste, et `react-refresh` interdit à un module de rendu d'exporter aussi des fonctions (cf. l'en-
// tête de `suisse/presentation.ts`, même raison, même conclusion).
//
// ⚠️ **Le serveur rend un instant, ce module en fait une durée.** Le calcul ne peut pas vivre côté
// serveur : la route est pollée toutes les 10 s, mais le rendu vit *entre* deux réponses, si bien
// qu'un « depuis 14 min » calculé là-bas afficherait 14 pendant dix secondes de plus. Les deux
// horloges sont en UTC et sur le même réseau local ; l'écart entre elles est sans effet sur une
// durée affichée à la minute.

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

/**
 * Ce qui attend une relance dans un créneau — ou `null` s'il n'y a rien à annoncer.
 *
 * ⚠️ **Compte les phases, pas les arrêts**, et c'est la lettre du CA (« 2 phases attendent votre
 * relance »). Un arrêt de portée « créneau » peut en avoir éteint quatre d'un coup : annoncer
 * « 1 pause » minimiserait ce que l'organisateur doit rallumer. Le geste reste **un bouton par
 * arrêt** (CA E05US033) — on compte ce qui est éteint, on ne multiplie pas les commandes.
 *
 * ⚠️ **Sans doublon.** Deux arrêts peuvent nommer la même phase : un arrêt de créneau qui l'a
 * coupée, puis un second armé qui la retrouve déjà en pause et la compte comme arrêtée. La
 * dédoublonner évite d'annoncer « 3 phases » sur une salle qui en compte deux — un chiffre faux
 * dans le sens qui **alarme**, donc celui qui use la vigilance le plus vite.
 *
 * ⚠️ **La durée est celle de la plus ancienne**, pas une moyenne ni la plus récente. C'est le
 * chiffre qui décide : « ça fait 25 minutes » appelle un geste, « ça fait 1 minute » non. Un arrêt
 * non daté (rien d'éteint encore) ne participe pas au calcul mais ne l'annule pas non plus.
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

/**
 * Peut-on proposer « bloquer dans x tours » sur cette phase ? (CA E05US034)
 *
 * ⚠️ **Extraite du JSX parce que c'est une règle, pas de la mise en page.** Quatre conditions, et
 * chacune correspond à un refus que le serveur prononcerait — offrir un geste dont on sait déjà
 * qu'il sera refusé est ce que la table des transitions de cycle de vie évite déjà par ailleurs.
 * Écrite dans une condition JSX, elle serait invisible au test, et c'est exactement le manque qui a
 * fait naître `suisse/presentation.ts` en revue d'E05US030.
 *
 * 1. **la phase est en cours** — une phase à venir n'a pas de tour d'où compter, une phase déjà en
 *    pause n'a rien à interrompre, une phase terminée non plus ;
 * 2. **le type annonce ses tours** (`TYPES_ARRETABLES`, miroir de la table de **même nom** côté
 *    domaine — elle a cessé de dériver de `TYPES_DEROULES` en E05US035, ADR-0093) —
 *    ailleurs l'arrêt serait accepté puis inerte, et l'organisateur le découvrirait le jour J ;
 * 3. **le tour courant est lisible** — sans origine, « dans x tours » ne se compte pas. Deviner
 *    couperait la salle au mauvais endroit ;
 * 4. **il reste un tour après celui qui tourne** — au dernier tour d'une phase (ronde 5 sur 5,
 *    la finale d'un tableau), `apres_tour = tourCourant + x - 1 >= nbTours` **quelle que soit** la
 *    valeur saisie, donc le serveur refuse à coup sûr (« ne couperait rien »). Sans cette
 *    condition, le formulaire s'ouvrait une fois par phase pour ne rendre qu'un 422 (revue
 *    E05US034).
 *
 * ⚠️ **`nbTours <= 1` compte comme non posable**, et il faut le dire : c'est la signature du repli
 * d'`avancement_bloc` (« je ne sais pas »), et une phase d'un seul tour n'a de toute façon aucune
 * frontière intérieure où couper.
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

/**
 * « Ronde 3 — tour 3 sur 5 » : le tour en cours, **lisible en tant que tel** (CA E05US034).
 *
 * ⚠️ **Extraite du JSX en revue, et le test a immédiatement servi.** Écrite en conditions de rendu,
 * la règle n'avait aucun oracle — et elle portait un repli qui affichait « **Tour 3** — tour 3 sur
 * 5 », le mot du repli redoublant la phrase qui le suit.
 *
 * ⚠️ **Ce repli n'était pas mort, contrairement à ce qu'un premier correctif a écrit** (rectifié en
 * 2ᵉ passe, axe adversarial). `libelle_de_tour` (`domain/tour_de_phase.py`) rend `null` pour toute
 * unité `PHASE_ENTIERE`, que le tour courant soit lisible ou non — pas seulement quand
 * `tour_courant` est `null`. Le cas est aujourd'hui inatteignable pour une autre raison (ces types
 * n'annoncent qu'un tour, donc `nbTours <= 1` les écarte une ligne plus haut), mais s'appuyer sur
 * une hypothèse fausse pour **supprimer** un repli aurait fait disparaître la ligne en silence le
 * jour où un tel type annoncerait plusieurs tours. On garde donc une phrase — sans préfixe
 * inventé : « tour 3 sur 5 » se lit très bien seul.
 *
 * `libelle_tour_courant` est **servi par le serveur**, jamais recomposé ici : la règle « à rebours
 * de la finale » a déjà deux domiciles (`DETTE-020`), et E05US032 interdit nommément d'en dériver un
 * troisième.
 *
 * Rend `null` — donc ne dit rien — quand la phase n'annonce pas de tour : une qualification est
 * *une* étape, elle ne se dit pas « tour 1 sur 1 ». Se taire vaut mieux qu'un compteur qui ne veut
 * rien dire. `nb_tours <= 1` couvre aussi la signature du repli d'`avancement_bloc` (« je ne sais
 * pas »).
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

/**
 * Ce que l'**écran de salle** doit annoncer d'une pause — ou rien du tout (CA E05US034).
 *
 * ⚠️ **Cette règle est née d'un bloquant de 2ᵉ passe, et le piège vaut d'être dit.** Le premier
 * correctif annonçait « le tir est suspendu » dès qu'**une** phase du créneau était en pause. Or la
 * portée par défaut d'un arrêt est **la phase seule**, et rien n'interdit deux phases en cours en
 * parallèle : l'écran projeté aurait donc annoncé au gymnase entier une suspension générale pendant
 * que le tableau d'à côté tirait. Sur une surface collective, une annonce non qualifiée fait
 * arrêter des gens que ça ne concerne pas — c'est pire que l'absence d'annonce qu'on venait de
 * corriger.
 *
 * Trois réponses, et une seule est « ne rien dire » :
 * - `null` — **aucune** phase en pause : l'écran se tait ;
 * - `[]` — plus rien ne tire : la salle est arrêtée, la phrase générale est vraie ;
 * - `['système suisse', …]` — il reste du tir en cours : on **nomme** ce qui est suspendu.
 *
 * Les phases `à venir` et `terminée` ne comptent dans aucun sens : elles ne tirent pas, donc leur
 * présence ne doit ni déclencher l'annonce ni empêcher la forme générale.
 */
export function phasesSuspendues(phases: readonly PhaseAffichable[]): string[] | null {
  const enPause = phases.filter((phase) => phase.statut === 'en_pause')
  if (enPause.length === 0) return null
  const tireEncore = phases.some((phase) => phase.statut === 'en_cours')
  if (!tireEncore) return []
  return enPause.map((phase) => nommerType(phase.type))
}

/**
 * Combien de tours on peut encore « bloquer d'avance » sur cette phase (CA E05US034).
 *
 * ⚠️ **Extraite pour être tenue en vis-à-vis du refus serveur** (correctif de revue, axe B). Le
 * serveur pose `apres_tour = tour_courant + x - 1` et refuse `apres_tour >= nb_tours` : la borne
 * du champ de saisie vaut donc exactement `nb_tours - tour_courant`. Écrite en dur dans le JSX,
 * cette coïncidence n'avait aucun oracle — et c'est la seule chose qui empêche les deux bornes de
 * diverger à la prochaine US, auquel cas l'écran offrirait un geste que le serveur refuse (ou
 * l'inverse, plus discret encore : il en interdirait un qui passe).
 *
 * N'a de sens que sur une phase que `peutPoserUnePause` accepte — qui garantit `tourCourant`
 * lisible et strictement inférieur à `nbTours`, donc un résultat d'au moins 1.
 */
export function toursBloquablesRestants(phase: PhasePosable): number {
  if (phase.tourCourant === null) return 0
  return Math.max(0, phase.nbTours - phase.tourCourant)
}
