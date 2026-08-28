// Le **modèle** du réglage de système suisse (E05US030) — logique pure, aucun React.
//
// Séparé du composant pour la raison habituelle : `react-refresh` interdit à un module de rendu
// d'exporter aussi des fonctions, et la conversion « écran ↔ serveur » se teste ici sans DOM. ⚠️
// **`rondesMaximales` est un miroir assumé du domaine** (`domain/suisse.py`). Le serveur fait
// autorité — il borne à la lecture et `EtapeDeroule` refuse une étape impossible —, mais l'atelier
// compose un format de **bibliothèque**, sans tournoi ni phase posée : aucune lecture à appeler. Sa
// dérive ne produirait qu'un avertissement faux, jamais un tournoi faux.

/** Le réglage tel que l'API le transporte, miroir de `ReglageSuisseDTO`. */
export interface ReglageSuisse {
  nb_rondes: number
}

/**
 * Ce que l'organisateur a choisi à l'écran — la forme **éditable**.
 *
 * Le nombre reste une **chaîne** : un champ vidé doit pouvoir rester vide pendant qu'on le retape,
 * ce qu'un `number` piloté perdrait à chaque frappe (même parti que `EtatPoules`).
 */
export interface EtatSuisse {
  rondes: string
}

/** Le nombre de rondes maximal accepté par l'API (`ReglageSuisseDTO.nb_rondes`, `le=64`). */
export const RONDES_MAX_REGLABLES = 64

/** Le réglage de départ d'un suisse neuf — 5 rondes, comme le défaut du domaine. */
export const SUISSE_PAR_DEFAUT: EtatSuisse = { rondes: '5' }

/** Reconstruit l'état d'édition depuis ce que porte l'étape (ou la phase). */
export function depuisReglage(reglage: ReglageSuisse | null): EtatSuisse {
  if (reglage === null) return SUISSE_PAR_DEFAUT
  return { rondes: String(reglage.nb_rondes) }
}

/**
 * Ce qui part au serveur — ou `undefined` quand la saisie n'est pas exploitable.
 *
 * Même convention que les deux autres formats : `undefined` veut dire « illisible », **pas**
 * « efface ». L'appelant ne le transmet jamais tel quel, il bloque sa soumission (`estValide`).
 */
export function versReglage(etat: EtatSuisse): ReglageSuisse | undefined {
  const nombre = Number(etat.rondes)
  if (etat.rondes.trim() === '' || !Number.isInteger(nombre)) return undefined
  if (nombre < 1 || nombre > RONDES_MAX_REGLABLES) return undefined
  return { nb_rondes: nombre }
}

/** Vrai si l'état est soumettable. */
export function estValide(etat: EtatSuisse): boolean {
  return versReglage(etat) !== undefined
}

/** Combien de rondes un effectif autorise sans qu'aucune paire ne se répète — miroir de
 * `domain/suisse.py::rondes_maximales`.
 *
 * À effectif **pair**, chacun a `n-1` adversaires et joue à chaque ronde : `n-1` rondes. À effectif
 * **impair**, chacun a encore `n-1` adversaires mais **chôme une fois** (le bye tourne), donc il
 * faut `n` rondes. ⚠️ Sous deux tireurs la réponse honnête est **0** et non 1 : aucune ronde n'est
 * appariable, et le service rend le même 0 sur une phase vide.
 */
export function rondesMaximales(effectif: number): number {
  if (!Number.isInteger(effectif) || effectif < 2) return 0
  return effectif % 2 === 0 ? effectif - 1 : effectif
}

/**
 * Dit la borne en clair, et **nomme l'écart** quand le réglage la dépasse.
 *
 * C'est tout l'objet du CA : la borne existait déjà côté domaine, mais l'organisateur ne la
 * découvrait qu'en se faisant refuser son étape (effectif déclaré) ou en voyant moins de rondes que
 * prévu le jour J (effectif réel — le service borne à la lecture, il ne lève pas). Un écran qui
 * montre la borne vaut mieux qu'un écran qui refuse.
 */
export function decrireBorne(effectif: number, nbRondes: number): string {
  return decrireBorneConnue(effectif, nbRondes, rondesMaximales(effectif))
}

/** La **même phrase**, mais sur une borne que l'appelant connaît déjà — celle du serveur.
 *
 * ⚠️ Cette variante existe pour une raison précise : l'écran de saisie a `rondes_maximales` dans sa
 * réponse d'état et ne doit **jamais** le recalculer — deux arithmétiques pour une même règle
 * divergent tôt ou tard. Réécrire la phrase à la main, ce qui avait été fait, a produit un texte
 * faux au cas limite (« 1 archers », et une raison qui n'était pas la bonne).
 */
export function decrireBorneConnue(effectif: number, nbRondes: number, maximum: number): string {
  if (maximum === 0) {
    const archers = effectif > 1 ? 'archers' : 'archer'
    return `${effectif} ${archers} : aucune ronde n’est appariable (il en faut au moins deux).`
  }
  const rondes = maximum > 1 ? 'rondes' : 'ronde'
  const borne = `${effectif} archers : ${maximum} ${rondes} au maximum sans que deux archers se rencontrent deux fois.`
  if (nbRondes <= maximum) return borne
  const jouees = maximum > 1 ? `les ${maximum} premières seront jouées` : 'une seule sera jouée'
  return `${borne} Vous en avez réglé ${nbRondes} : ${jouees}.`
}
