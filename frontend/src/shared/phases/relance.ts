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

import { TYPES_ARRETABLES } from './catalogue'
import type { TypePhase } from './catalogue'

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
 * `Phase` + `AvancementBloc`, pour que `shared/` ne dépende d'aucune feature. */
export interface PhasePosable {
  statut: string
  type: TypePhase
  tourCourant: number | null
  nbTours: number
}

/**
 * Peut-on proposer « bloquer dans x tours » sur cette phase ? (CA E05US034)
 *
 * ⚠️ **Extraite du JSX parce que c'est une règle, pas de la mise en page.** Trois conditions, et
 * chacune correspond à un refus que le serveur prononcerait — offrir un geste dont on sait déjà
 * qu'il sera refusé est ce que la table des transitions de cycle de vie évite déjà par ailleurs.
 * Écrite dans une condition JSX, elle serait invisible au test, et c'est exactement le manque qui a
 * fait naître `suisse/presentation.ts` en revue d'E05US030.
 *
 * 1. **la phase est en cours** — une phase à venir n'a pas de tour d'où compter, une phase déjà en
 *    pause n'a rien à interrompre, une phase terminée non plus ;
 * 2. **le type annonce ses tours** (`TYPES_ARRETABLES`, miroir de `TYPES_DEROULES` côté domaine) —
 *    ailleurs l'arrêt serait accepté puis inerte, et l'organisateur le découvrirait le jour J ;
 * 3. **le tour courant est lisible** — sans origine, « dans x tours » ne se compte pas. Deviner
 *    couperait la salle au mauvais endroit.
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
    phase.nbTours > 1
  )
}
