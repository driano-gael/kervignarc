// Présentation des doublons détectés (E02US005) — logique **pure** (testée sans rendu, E00US014).
//
// Le serveur renvoie les paires déjà triées (probable avant à vérifier). Ici on ne fait que les
// **répartir sous un titre lisible** — aucune règle métier, qui vit côté domaine Python
// (`domain/doublons.py`).

import type { Doublon } from './api'

// Les deux niveaux du serveur, du plus sûr au plus douteux, avec le mot qui les dit **sur une
// ligne d'archer**. L'ordre de ce tableau **est** l'ordre de certitude : le premier gagne quand un
// archer est rapproché de plusieurs fiches.
//
// ⚠️ Le singulier est délibéré. Ces libellés titraient des groupes (« Doublons probables ») tant
// qu'un écran dédié les empilait ; depuis E16US010 le signalement vit **sur la ligne**, où il
// qualifie une fiche et non un tas.
const NIVEAUX = [
  { niveau: 'probable', libelle: 'Doublon probable' },
  { niveau: 'a_verifier', libelle: 'Doublon à vérifier' },
] as const

export interface SignalementDoublon {
  niveau: string
  libelle: string
  /** Les paires où cet archer figure — souvent une, parfois plusieurs. */
  paires: Doublon[]
}

/**
 * Ce qu'il faut signaler **sur la ligne d'un archer**, ou `null` si rien ne le rapproche (CA
 * E16US010 : « une simple icône cliquable sur la ligne de l'archer peut suffire »).
 *
 * ⚠️ Le niveau retenu est **le plus certain** de ses paires : un archer à la fois « probable » et
 * « à vérifier » doit se lire au plus fort, sinon le signalement le plus sûr disparaît derrière le
 * plus douteux.
 */
export function signalementPour(archerId: number, doublons: Doublon[]): SignalementDoublon | null {
  const siennes = doublons.filter((d) => d.a.id === archerId || d.b.id === archerId)
  if (siennes.length === 0) return null
  const niveau = NIVEAUX.find(({ niveau }) => siennes.some((d) => d.niveau === niveau))
  // Un niveau inconnu (serveur en avance sur le front) ne fait pas disparaître le signalement :
  // mieux vaut « fiches qui se ressemblent » sans qualificatif qu'un archer signalé nulle part.
  return {
    niveau: niveau?.niveau ?? 'inconnu',
    libelle: niveau?.libelle ?? 'Fiche à vérifier',
    paires: siennes,
  }
}
