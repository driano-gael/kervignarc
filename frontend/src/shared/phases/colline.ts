// Le **modèle** du réglage de colline (E05US027) — logique pure, aucun React.
//
// Séparé du composant pour la raison habituelle : `react-refresh` interdit à un module de rendu
// d'exporter aussi des fonctions. ⚠️ **`porteeMaximale` est un miroir assumé du domaine** : le
// serveur borne à la lecture et refuse une étape impossible, mais l'atelier compose aussi un format
// de **bibliothèque**, sans lecture à appeler. ⚠️ **Deux champs, là où les trois autres formats
// n'en ont qu'un** : la portée distingue le **King of the Hill** du **Ladder**, que le référentiel
// §10.1 présente comme deux formats et qui sont deux réglages d'un même type.

/** Le réglage tel que l'API le transporte, miroir de `ReglageCollineDTO`. */
export interface ReglageColline {
  nb_manches: number
  portee_de_defi: number
}

/**
 * Ce que l'organisateur a choisi à l'écran — la forme **éditable**.
 *
 * Les nombres restent des **chaînes** : un champ vidé doit pouvoir rester vide pendant qu'on le
 * retape, ce qu'un `number` piloté perdrait à chaque frappe (même parti que `EtatPoules` et
 * `EtatSuisse`).
 */
export interface EtatColline {
  manches: string
  portee: string
}

/** Les bornes acceptées par l'API (`ReglageCollineDTO`, `le=64` sur les deux champs). */
export const MANCHES_MAX_REGLABLES = 64
export const PORTEE_MAX_REGLABLE = 64

/** Le réglage de départ d'une colline neuve — 5 manches en King of the Hill. */
export const COLLINE_PAR_DEFAUT: EtatColline = { manches: '5', portee: '1' }

/** Reconstruit l'état d'édition depuis ce que porte l'étape (ou la phase). */
export function depuisReglage(reglage: ReglageColline | null): EtatColline {
  if (reglage === null) return COLLINE_PAR_DEFAUT
  return { manches: String(reglage.nb_manches), portee: String(reglage.portee_de_defi) }
}

/**
 * Ce qui part au serveur — ou `undefined` quand la saisie n'est pas exploitable.
 *
 * Même convention que les trois autres formats : `undefined` veut dire « illisible », **pas**
 * « efface ». L'appelant ne le transmet jamais tel quel, il bloque sa soumission (`estValide`).
 */
export function versReglage(etat: EtatColline): ReglageColline | undefined {
  const manches = Number(etat.manches)
  const portee = Number(etat.portee)
  if (etat.manches.trim() === '' || !Number.isInteger(manches)) return undefined
  if (etat.portee.trim() === '' || !Number.isInteger(portee)) return undefined
  if (manches < 1 || manches > MANCHES_MAX_REGLABLES) return undefined
  if (portee < 1 || portee > PORTEE_MAX_REGLABLE) return undefined
  return { nb_manches: manches, portee_de_defi: portee }
}

/** Vrai si l'état est soumettable. */
export function estValide(etat: EtatColline): boolean {
  return versReglage(etat) !== undefined
}

/**
 * Le nom du format que cette portée désigne — c'est **le** repère de l'organisateur.
 *
 * Le catalogue n'expose qu'un type « colline », parce que le moteur est le même (règle 2). Mais le
 * club, lui, dit « King of the Hill » ou « Ladder », et le référentiel §10.1 les décrit séparément.
 * Nommer le format sous le champ est ce qui rattache le réglage au vocabulaire de la salle.
 */
export function nommerFormat(portee: number): string {
  return portee <= 1 ? 'King of the Hill' : 'Ladder'
}

/**
 * La portée la plus grande qu'un effectif autorise — miroir de
 * `domain/colline.py::portee_maximale`.
 *
 * Un défi ne peut pas porter au-delà du dernier rang : la borne est `effectif - 1`. ⚠️ Sous deux
 * tireurs, la réponse honnête est **0** et non 1 : aucun défi n'est appariable. Le service rend le
 * même 0 sur une phase vide.
 */
export function porteeMaximale(effectif: number): number {
  if (!Number.isInteger(effectif) || effectif < 2) return 0
  return effectif - 1
}

/**
 * Dit la borne en clair, et **nomme l'écart** quand le réglage la dépasse.
 *
 * C'est l'objet du CA, et le jumeau exact de `decrireBorne` du suisse : la borne existait déjà côté
 * domaine, mais l'organisateur ne la découvrait qu'en se faisant refuser son étape (effectif
 * déclaré) ou en voyant des défis plus courts que prévu le jour J (effectif réel — le service borne
 * à la lecture, il ne lève pas). Un écran qui montre la borne vaut mieux qu'un écran qui refuse.
 */
export function decrireBorne(effectif: number, portee: number): string {
  return decrireBorneConnue(effectif, portee, porteeMaximale(effectif), 'refuse')
}

/** La **même phrase**, mais sur une borne que l'appelant connaît déjà — celle du serveur.
 *
 * ⚠️ Cette variante existe pour la raison qu'`api.ts` documente : l'écran de saisie a
 * `portee_maximale` dans sa réponse d'état et ne doit **jamais** le recalculer — deux arithmétiques
 * pour une même règle divergent tôt ou tard. Réécrire la phrase à la main est ce qui avait produit
 * un texte faux au cas limite chez le suisse (« 1 archers »).
 */
export type RegimeDeBorne = 'borne' | 'refuse'

export function decrireBorneConnue(
  effectif: number,
  portee: number,
  maximum: number,
  regime: RegimeDeBorne = 'borne',
): string {
  if (maximum === 0) {
    const archers = effectif > 1 ? 'archers' : 'archer'
    return `${effectif} ${archers} : aucun défi n’est appariable (il en faut au moins deux).`
  }
  const rangs = maximum > 1 ? 'rangs' : 'rang'
  const borne = `${effectif} archers : un défi porte au plus sur ${maximum} ${rangs}.`
  if (portee <= maximum) return borne
  // ⚠️ **Les deux régimes ne disent PAS la même chose, et un correctif de revue les avait
  // inversés.** Ce qui se passe au-delà de la borne dépend d'où vient l'effectif : sur l'effectif
  // **réel** du créneau (`'borne'`), `ServiceColline` **borne à la lecture** et ne lève pas, donc
  // le réglage excédentaire est réellement joué, en plus court ; sur l'effectif **déclaré**
  // (`'refuse'`), `EtapeDeroule` **lève** et l'enregistrement rend 422. Dire « seront appliqués »
  // dans le second cas, c'est un feu vert suivi d'un mur — ce que le CA existe pour supprimer.
  if (regime === 'refuse') {
    return `${borne} Vous avez réglé ${portee} : réduisez la portée, sinon l’enregistrement sera refusé.`
  }
  const applique = maximum > 1 ? `${maximum} rangs seront appliqués` : 'un seul rang sera appliqué'
  return `${borne} Vous avez réglé ${portee} : ${applique}.`
}
