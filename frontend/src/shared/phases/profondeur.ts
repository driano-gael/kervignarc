// Le **modèle** du réglage « jusqu'où classer » (E06US006, ADR-0070) — logique pure, aucun React.
//
// Séparé du composant pour deux raisons : la règle `react-refresh` interdit à un module de rendu
// d'exporter aussi des fonctions, et surtout ces trois fonctions sont **le cœur du tri-état**, celui
// que la revue a désigné comme la cause du seul bloquant de l'US. Elles se testent ici sans monter
// le moindre DOM.

import type { Profondeur } from './catalogue'

/** Les rangs qu'un tableau à petite finale décerne — miroir de `RANGS_DU_PODIUM` côté domaine. */
export const RANGS_DU_PODIUM = 4

/**
 * Ce que l'organisateur a choisi à l'écran — la forme **éditable**, distincte de ce qui part au
 * serveur.
 *
 * `seuil` reste une **chaîne** : un champ numérique vidé doit pouvoir rester vide pendant qu'on le
 * retape, ce qu'un `number` piloté ferait perdre à chaque frappe (même parti que l'effectif simulé
 * et que le barème). C'est aussi ce qui permet de distinguer « en cours de saisie » de « invalide ».
 */
export type EtatProfondeur =
  { mode: 'preset' } | { mode: 'integral' } | { mode: 'top'; seuil: string }

/** L'état d'une phase qui ne règle rien — le point de départ de tout formulaire. */
export const PROFONDEUR_AU_PRESET: EtatProfondeur = { mode: 'preset' }

/** Reconstruit l'état d'édition depuis ce que porte la phase (ou le modèle d'étape). */
export function depuisProfondeur(profondeur: Profondeur | null): EtatProfondeur {
  if (profondeur === null) return PROFONDEUR_AU_PRESET
  if (profondeur.nom === 'un_vers_n') return { mode: 'integral' }
  return { mode: 'top', seuil: String(profondeur.jusqu_au ?? RANGS_DU_PODIUM) }
}

/**
 * Ce qui part au serveur — ou `undefined` quand la saisie n'est pas exploitable.
 *
 * `undefined` reprend la convention de `lireEntier` (« illisible »), et non celle de
 * `ConfigPhase.profondeur?` (« clé omise, donc efface »). Les deux sens opposés du même jeton, à
 * deux modules d'écart, sont ce que la revue a relevé : l'appelant ne doit jamais transmettre ce
 * `undefined` tel quel — il bloque sa soumission (`estValide`).
 */
export function versProfondeur(etat: EtatProfondeur): Profondeur | null | undefined {
  if (etat.mode === 'preset') return null
  if (etat.mode === 'integral') return { nom: 'un_vers_n', jusqu_au: null }
  const seuil = Number(etat.seuil)
  if (etat.seuil.trim() === '' || !Number.isInteger(seuil) || seuil < 1) return undefined
  return { nom: 'top_n', jusqu_au: seuil }
}

/** Vrai si l'état est soumettable — « je m'arrête à un rang » sans dire lequel ne l'est pas. */
export function estValide(etat: EtatProfondeur): boolean {
  return versProfondeur(etat) !== undefined
}

/** Dit une profondeur en clair — « classement intégral » / « classé jusqu'au 8ᵉ ».
 *
 * Domicilié ici plutôt que dans une feature : les **deux** écrans de composition l'affichent
 * désormais, et le laisser dans `features/deroule` obligeait `features/phases` à y puiser. */
export function decrireProfondeur(profondeur: Profondeur): string {
  if (profondeur.nom === 'un_vers_n') return 'classement intégral'
  return `classé jusqu'au ${profondeur.jusqu_au}ᵉ`
}
