// Ce que l'écran du système suisse **dit** — logique pure, aucun React (E05US030).
//
// Extrait de `SaisieSuisse.tsx` en revue, pour la raison que `shared/phases/suisse.ts` énonce en
// tête : `react-refresh` interdit à un module de rendu d'exporter aussi des fonctions, donc tout ce
// qui vit dans le `.tsx` est **intestable**. C'était un vrai manque et pas une préférence de style :
// deux des fonctions ci-dessous portent un CA de l'US — la conversion des points en victoires, et
// la phrase qui explique pourquoi la ronde suivante n'est pas là —, et la fiche de recette
// (`docs/fonctionnel/E05US030.md`) désigne nommément la première comme « à vérifier à la main ».
// Un calcul dont la recette dit « vérifiez que… » mérite un test.

import type { Duelliste } from '../saisie-duels/api'
import type { RencontreSuisse } from './api'

/** La forme d'une ronde dont ce module a besoin — commune aux deux vues (saisie et rédigée).
 *
 * Volontairement pauvre : ni pavé, ni score. Ce qui suit ne sert qu'à **nommer** et à **compter**,
 * et le typer sur `Ronde` interdirait de le réutiliser sur l'écran d'organisation, qui lit la
 * photo rédigée. */
export interface RondeLisible {
  numero: number
  close: boolean
  bye: Duelliste | null
  rencontres: { haut: Duelliste | null; bas: Duelliste | null }[]
}

/**
 * Les points, rendus **en points réels**.
 *
 * ⚠️ Le serveur les transporte en **demi-points doublés** (victoire = 2, nul = 1) pour ne comparer
 * que des entiers — une égalité de départage ne doit pas reposer sur un flottant. C'est donc à
 * l'affichage de rendre la moitié : servir le nombre brut annoncerait « 6 victoires » à qui en a
 * trois. Le `buchholz` est dans la **même unité** (c'est une somme de ces points), donc il passe
 * par la même fonction.
 */
export function decrirePoints(doubles: number): string {
  return doubles % 2 === 0 ? String(doubles / 2) : `${Math.floor(doubles / 2)},5`
}

/** L'état d'une rencontre en un mot — le même vocabulaire que les duels et les poules. */
export function etatRencontre(rencontre: RencontreSuisse): string {
  if (rencontre.desynchronisee) return 'tir mis de côté — population à rétablir'
  const duel = rencontre.duel
  if (duel.validee_par !== null) return 'validée'
  if (duel.validation_en_attente === true) return 'validation en attente'
  if (duel.resultat?.termine === true) return 'à valider'
  if (duel.manches.length > 0) return 'en cours'
  return 'à tirer'
}

/** Des places de tir en toutes lettres, **groupées par cible**.
 *
 * ⚠️ **Domiciliée dans `shared/salle/place.ts` depuis E05US031** — auprès du type qu'elle manipule,
 * l'onglet « En cours » en ayant besoin pour les poules autant que pour le suisse. Ré-exportée ici
 * pour qu'aucun import existant ne casse ; les appelants neufs prennent le chemin `shared/`.
 */
export { decrirePlaces } from '../../shared/salle/place'

/** Ce que l'écran a à dire **sous** la liste des rondes — le CA de l'attente nommée.
 *
 * Trois états, et les trois comptent :
 * - `attente` — la ronde en cours n'est pas close et il en reste à jouer : on dit **pourquoi** la
 *   suivante n'est pas là, sinon il ne reste qu'une absence, et le scoreur ne peut pas distinguer
 *   « plus rien à jouer » de « il reste des rencontres à saisir » ;
 * - `fini` — toutes les rondes dues sont jouées et closes : le classement est définitif ;
 * - `null` — la dernière ronde due est **en cours** : il n'y a pas de ronde suivante à promettre,
 *   et rien n'est terminé non plus. Se taire est alors la seule réponse juste.
 */
export type MotDeLaFin =
  { etat: 'attente'; courante: number; suivante: number } | { etat: 'fini' } | null

export function motDeLaFin(rondes: readonly RondeLisible[], rondesDues: number): MotDeLaFin {
  const derniere = rondes[rondes.length - 1] ?? null
  if (derniere === null || rondesDues === 0) return null
  if (!derniere.close) {
    return rondes.length < rondesDues
      ? { etat: 'attente', courante: derniere.numero, suivante: derniere.numero + 1 }
      : null
  }
  return rondes.length >= rondesDues ? { etat: 'fini' } : null
}

/** Le nom d'un archer, retrouvé dans les rondes affichées — `#id` si personne ne le porte.
 *
 * Le repli est inatteignable en pratique (la ronde 1 contient chaque participant, en rencontre ou
 * en bye, et le classement est vide en deçà de deux tireurs), mais il vaut mieux qu'un `undefined`
 * rendu à l'écran.
 */
export function nomDeLArcher(rondes: readonly RondeLisible[], archerId: number): string {
  for (const ronde of rondes) {
    for (const r of ronde.rencontres) {
      if (r.haut?.archer_id === archerId) return `${r.haut.nom} ${r.haut.prenom}`
      if (r.bas?.archer_id === archerId) return `${r.bas.nom} ${r.bas.prenom}`
    }
    if (ronde.bye?.archer_id === archerId) return `${ronde.bye.nom} ${ronde.bye.prenom}`
  }
  return `#${archerId}`
}

/** Ce qui **manque** dans une ronde en cours, nommé (CA E05US034).
 *
 * ⚠️ **Deux listes et pas une**, et c'est la lettre du CA : *« quelles rencontres ne sont pas
 * validées, et lesquelles ne sont pas encore saisies »*. La distinction décide de qui doit agir —
 * une rencontre non saisie attend le **scoreur de sa cible**, une rencontre saisie et non validée
 * attend un **geste de validation**. Les confondre dans un seul « il manque 3 rencontres » renvoie
 * l'organisateur chercher partout, ce que le refus existe précisément pour éviter (`P-3` : un refus
 * qui ne dit pas quoi faire est un cul-de-sac).
 *
 * L'ancien message ne comptait que : *« la ronde en cours n'est pas entièrement saisie »*. Vrai, et
 * inutilisable le jour J dans un gymnase où quatorze rencontres se jouent en parallèle.
 *
 * Une rencontre **désynchronisée** est rangée à part : elle n'attend ni saisie ni validation mais
 * un rétablissement de population (ADR-0049 §4), et l'annoncer comme « à saisir » enverrait le
 * scoreur buter sur un tir que le serveur refuse d'écraser.
 */
export interface CeQuiManque {
  aSaisir: string[]
  aValider: string[]
  bloquees: string[]
}

export function ceQuiManque(rencontres: readonly RencontreSuisse[]): CeQuiManque {
  const manque: CeQuiManque = { aSaisir: [], aValider: [], bloquees: [] }
  for (const rencontre of rencontres) {
    const nom = nommerRencontre(rencontre)
    if (rencontre.desynchronisee) {
      manque.bloquees.push(nom)
      continue
    }
    const duel = rencontre.duel
    if (duel.validee_par !== null) continue
    // ⚠️ **`resultat.termine` et non `manches.length > 0`** : une rencontre à demi tirée n'est pas
    // « à valider », elle est encore à saisir. Le classement de `etatRencontre` juste au-dessus
    // fait la même lecture, et la refaire autrement ici ferait diverger deux phrases du même écran.
    if (duel.resultat?.termine === true) manque.aValider.push(nom)
    else manque.aSaisir.push(nom)
  }
  return manque
}

/** « Martin D. – Le Goff Y. », ou la place de tir si un côté manque (bye tardif, population mouvante). */
function nommerRencontre(rencontre: RencontreSuisse): string {
  const cote = (duelliste: Duelliste | null) =>
    duelliste === null ? '?' : `${duelliste.nom} ${duelliste.prenom}`
  return `${cote(rencontre.haut)} – ${cote(rencontre.bas)}`
}
