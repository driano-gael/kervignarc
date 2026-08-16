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
import type { Place } from '../../shared/salle/place'
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
 * Un bloc de couloirs est contigu dans la salle *mise à plat*, pas sur une seule cible : les deux
 * places d'une rencontre peuvent chevaucher deux cibles.
 */
export function decrirePlaces(places: readonly Place[]): string {
  const parCible = new Map<number, string[]>()
  for (const [cible, couloir] of places) {
    parCible.set(cible, [...(parCible.get(cible) ?? []), couloir])
  }
  return [...parCible.entries()]
    .map(([cible, couloirs]) => `cible ${cible} : ${couloirs.join(', ')}`)
    .join(' · ')
}

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
