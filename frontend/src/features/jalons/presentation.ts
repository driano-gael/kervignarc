// Dérivation **pure** du verdict d'un jalon (E16US012) — isolée du rendu React pour être testée en
// node, comme `completude/presentation.ts` ou `supervision/etat.ts`.
//
// **Pourquoi un verdict écrit, et pas seulement la liste.** Le CA dit que l'écran répond à *une
// question binaire*. Une liste d'états y répond implicitement — il faut la lire en entier et savoir
// lesquelles bloquent. La phrase, elle, répond tout de suite ; la liste dit ensuite *pourquoi*.

import type { NiveauPreparation } from './api'

export type TonVerdict = 'ok' | 'alerte'

export interface Verdict {
  ton: TonVerdict
  texte: string
}

// Les **trois** cas, et pas deux : `pret` seul ne suffit pas à écrire la phrase.
//
// C'est l'asymétrie de la famille (ADR-0096) : « il manque quelque chose » se dit différemment
// selon que le serveur **refusera** (démarrer) ou **laissera passer** (terminer, sans garde dure).
// ⚠️ **`moment` dit *quand* le refus tombe** : un jalon répond de l'**étape**, pas du prochain clic
// — depuis *brouillon*, « Marquer prêt » n'exige que les créneaux, et « ce qui manque sera refusé »
// se lisait comme un refus **immédiat**, démenti au clic suivant (relevé par l'axe D). Nommer le
// moment rend la phrase vraie dans les deux cas.
export function verdict(pret: boolean, bloquant: boolean, moment?: string | null): Verdict {
  if (pret) return { ton: 'ok', texte: 'Oui — rien ne s’y oppose.' }
  if (bloquant) {
    const quand = moment ? ` ${moment}` : ''
    return { ton: 'alerte', texte: `Pas encore — ce qui manque ci-dessous sera refusé${quand}.` }
  }
  return {
    ton: 'alerte',
    texte: 'Il reste des choses à faire — l’application ne vous en empêchera pas.',
  }
}

// --- La pastille de la liste des tournois (E16US010) ------------------------------------------

export interface Pastille {
  libelle: string
  /** L'escalade — `--danger-strong` plutôt que `--danger`, le rouge restant exclu (`DV-03`). */
  fort: boolean
}

/**
 * Ce qu'affiche la pastille d'un niveau, ou `null` si elle ne s'allume pas.
 *
 * ⚠️ Le libellé est **du texte**, pas seulement une couleur : une pastille qui ne signale que par
 * la teinte n'est lisible ni au daltonisme ni au lecteur d'écran. La cause chiffrée, elle, vient
 * du serveur (`resume`) — c'est la phrase du refus lui-même.
 */
export function pastille(niveau: NiveauPreparation): Pastille | null {
  if (niveau === 'alerte') return { libelle: 'Ne peut pas démarrer', fort: true }
  if (niveau === 'avertissement') return { libelle: 'À compléter', fort: false }
  return null
}
