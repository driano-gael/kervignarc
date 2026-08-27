// Ce que l'écran de la colline **dit** — logique pure, aucun React (E05US027).
//
// Séparé du `.tsx` pour la raison que `shared/phases/colline.ts` énonce en tête : `react-refresh`
// interdit à un module de rendu d'exporter aussi des fonctions, donc tout ce qui vit dans le `.tsx`
// est **intestable**. Ce module porte deux CA de l'US — la phrase qui explique pourquoi la manche
// suivante n'est pas là, et le fait que les archers au repos soient **nommés** plutôt que
// silencieusement absents — donc il mérite ses tests.

import type { Duelliste } from '../saisie-duels/api'
import type { Defi } from './api'

/** L'état d'un défi en un mot — le vocabulaire commun aux duels, aux poules et au suisse.
 *
 * ⚠️ **Importée de `shared/duels/etatDeSaisie.ts`, pas recopiée.** C'est le rendez-vous que la
 * revue d'E05US030 avait posé : la fonction était écrite deux fois (poules, suisse) à l'identique,
 * et la colline en aurait fait une 3ᵉ par mimétisme. Elle est remontée en `shared/` dans cette US.
 */
export { etatRencontreDeSaisie as etatDefi } from '../../shared/duels/etatDeSaisie'

/** Des places de tir en toutes lettres, **groupées par cible** — domiciliée en `shared/`. */
export { decrirePlaces } from '../../shared/salle/place'

/** La forme d'une manche dont ce module a besoin — commune aux deux vues (saisie et rédigée).
 *
 * Volontairement pauvre : ni pavé, ni score. Ce qui suit ne sert qu'à **nommer** et à **compter**,
 * et le typer sur `Manche` interdirait de le réutiliser sur l'écran d'organisation, qui lit la
 * photo rédigée — même parti que `RondeLisible` chez le suisse.
 */
export interface MancheLisible {
  numero: number
  close: boolean
  au_repos: Duelliste[]
  defis: { haut: Duelliste | null; bas: Duelliste | null }[]
}

/** Le nom du format que cette portée désigne, pour l'en-tête de l'écran. */
export { nommerFormat } from '../../shared/phases/colline'

/**
 * Comment un défi se lit : « le 6 défie le 4 ».
 *
 * ⚠️ **C'est le vocabulaire du format, et il n'est pas interchangeable avec celui d'un duel.** Une
 * rencontre de poule ou de ronde oppose deux archers sans hiérarchie préalable ; ici l'un **défie**
 * l'autre depuis une position plus basse, et c'est toute la lecture du format — le public suit des
 * positions qui montent et descendent. Dire « MARTIN contre DURAND » perdrait l'information.
 */
export function decrireDefi(positionHaute: number, positionBasse: number): string {
  return `le ${positionBasse} défie le ${positionHaute}`
}

/** Ce que l'écran a à dire **sous** la liste des manches — le CA de l'attente nommée.
 *
 * Trois états, calqués sur `motDeLaFin` du suisse : `attente` dit **pourquoi** la manche suivante
 * n'est pas là — et la raison est ici plus forte, les défis suivants se calculant sur les
 * **positions** issues de la manche en cours ; `fini` dit que la colline est définitive ; `null`
 * quand la dernière manche due est **en cours** — rien à promettre, se taire est la seule réponse.
 */
export type MotDeLaFin =
  { etat: 'attente'; courante: number; suivante: number } | { etat: 'fini' } | null

export function motDeLaFin(manches: readonly MancheLisible[], manchesDues: number): MotDeLaFin {
  const derniere = manches[manches.length - 1] ?? null
  if (derniere === null || manchesDues === 0) return null
  if (!derniere.close) {
    return manches.length < manchesDues
      ? { etat: 'attente', courante: derniere.numero, suivante: derniere.numero + 1 }
      : null
  }
  // ⚠️ **Ce repli n'est PAS mort, mais il ne se déclenche pas contre notre serveur** (relevé en
  // revue). `_rejouer` ne s'arrête que sur une manche non close, donc une dernière manche close
  // implique que toutes les manches dues l'ont été : `manches.length >= manchesDues` est vrai à ce
  // point, dans toute réponse cohérente. Il est gardé parce qu'il **couvre une réponse serveur
  // incohérente** — le jour où le rejeu changerait de règle d'arrêt, dire « fini » sur une phase
  // qui ne l'est pas serait pire que se taire. Ne pas le simplifier en `{ etat: 'fini' }` sans
  // avoir rouvert `ServiceColline._rejouer` : c'est là qu'est l'invariant, pas ici.
  return manches.length >= manchesDues ? { etat: 'fini' } : null
}

/** Les archers **au repos** d'une manche, nommés.
 *
 * ⚠️ **Ce n'est pas le « bye » du suisse, et les confondre serait faux sur le fond** : un bye est
 * un archer **désigné** qui gagne d'office et marque des points ; ici personne ne gagne rien. Ils
 * sont nommés plutôt qu'omis parce que le scoreur les cherche — à portée 1, ce sont les **deux
 * extrémités** de la colline à chaque manche paire, quel que soit l'effectif.
 */
export function nommerAuRepos(manche: MancheLisible): string[] {
  return manche.au_repos.map((qui) => `${qui.nom} ${qui.prenom}`)
}

/** Le nom d'un archer, retrouvé dans les manches affichées — `#id` si personne ne le porte.
 *
 * Le repli est inatteignable en pratique (la manche 1 à portée 1 contient chaque participant, en
 * défi ou au repos), mais il vaut mieux qu'un `undefined` rendu à l'écran.
 */
export function nomDeLArcher(manches: readonly MancheLisible[], archerId: number): string {
  for (const manche of manches) {
    for (const defi of manche.defis) {
      if (defi.haut?.archer_id === archerId) return `${defi.haut.nom} ${defi.haut.prenom}`
      if (defi.bas?.archer_id === archerId) return `${defi.bas.nom} ${defi.bas.prenom}`
    }
    for (const qui of manche.au_repos) {
      if (qui.archer_id === archerId) return `${qui.nom} ${qui.prenom}`
    }
  }
  return `#${archerId}`
}

/** Ce qui **manque** dans une manche en cours, nommé — jumeau de `ceQuiManque` du suisse.
 *
 * Quatre listes, et la distinction décide de **qui doit agir** : un défi non saisi attend le
 * scoreur de sa cible, un défi saisi et non validé attend un geste de validation, un défi en file
 * attend le **réseau** (personne n'a rien à faire), un défi bloqué attend un rétablissement de
 * population (ADR-0049 §4). Les confondre dans un « il manque 3 défis » renvoie l'organisateur
 * chercher partout — le cul-de-sac que `P-3` interdit.
 */
export interface CeQuiManque {
  aSaisir: string[]
  aValider: string[]
  enFile: string[]
  bloques: string[]
}

export function ceQuiManque(defis: readonly Defi[]): CeQuiManque {
  const manque: CeQuiManque = { aSaisir: [], aValider: [], enFile: [], bloques: [] }
  for (const defi of defis) {
    const nom = nommerDefi(defi)
    if (defi.desynchronisee) {
      manque.bloques.push(nom)
      continue
    }
    const duel = defi.duel
    if (duel.validee_par !== null) continue
    // Une validation mise en file hors-ligne a sa **propre** ligne : elle attend le réseau, pas une
    // personne. C'est l'arbitrage de la revue d'E05US034, repris ici d'emblée — la ranger dans
    // `aValider` enverrait réclamer un geste déjà posé, et l'écarter tout court laisserait le
    // résumé **vide** sous une phrase d'attente si c'était le dernier défi.
    if (duel.validation_en_attente === true) {
      manque.enFile.push(nom)
      continue
    }
    // ⚠️ **`resultat.termine` et non `manches.length > 0`** : un défi à demi tiré n'est pas « à
    // valider », il est encore à saisir. `etatDefi` fait la même lecture, et la refaire autrement
    // ici ferait diverger deux phrases du même écran.
    if (duel.resultat?.termine === true) manque.aValider.push(nom)
    else manque.aSaisir.push(nom)
  }
  return manque
}

/** « le 6 défie le 4 — MARTIN Jean / LE GOFF Yann », ou `?` si un côté manque. */
function nommerDefi(defi: Defi): string {
  const cote = (duelliste: Duelliste | null) =>
    duelliste === null ? '?' : `${duelliste.nom} ${duelliste.prenom}`
  const positions = decrireDefi(defi.position_haute, defi.position_basse)
  return `${positions} — ${cote(defi.haut)} / ${cote(defi.bas)}`
}
