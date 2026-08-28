// Ce que l'écran du système suisse **dit** — logique pure, aucun React (E05US030).
//
// Extrait de `SaisieSuisse.tsx` en revue : `react-refresh` interdit à un module de rendu d'exporter
// aussi des fonctions, donc tout ce qui vit dans le `.tsx` est **intestable**. Vrai manque et non
// préférence de style — deux des fonctions ci-dessous portent un CA de l'US, et la fiche de recette
// désigne nommément la première comme « à vérifier à la main ». Un calcul dont la recette dit «
// vérifiez que… » mérite un test.

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

/** Les points, rendus **en points réels**.
 *
 * ⚠️ Le serveur les transporte en **demi-points doublés** (victoire = 2, nul = 1) pour ne comparer
 * que des entiers — une égalité de départage ne doit pas reposer sur un flottant. C'est donc à
 * l'affichage de rendre la moitié : servir le nombre brut annoncerait « 6 victoires » à qui en a
 * trois. Le `buchholz` est dans la **même unité**, donc il passe par la même fonction.
 */
export function decrirePoints(doubles: number): string {
  return doubles % 2 === 0 ? String(doubles / 2) : `${Math.floor(doubles / 2)},5`
}

/** L'état d'une rencontre en un mot — le même vocabulaire que les duels, les poules et la colline.
 *
 * ⚠️ **Domiciliée dans `shared/duels/etatDeSaisie.ts` depuis E05US027**, sous le nom
 * `etatRencontreDeSaisie` — la colline en était la 3ᵉ occurrence, et c'est le rendez-vous que la
 * revue de cette US-ci avait posé. Ré-exportée ici sous son ancien nom pour qu'aucun import
 * existant ne casse ; les appelants neufs prennent le chemin `shared/`. Même geste que
 * `decrirePlaces` juste en dessous.
 */
export { etatRencontreDeSaisie as etatRencontre } from '../../shared/duels/etatDeSaisie'

/** Des places de tir en toutes lettres, **groupées par cible**.
 *
 * ⚠️ **Domiciliée dans `shared/salle/place.ts` depuis E05US031** — auprès du type qu'elle manipule,
 * l'onglet « En cours » en ayant besoin pour les poules autant que pour le suisse. Ré-exportée ici
 * pour qu'aucun import existant ne casse ; les appelants neufs prennent le chemin `shared/`.
 */
export { decrirePlaces } from '../../shared/salle/place'

/** Ce que l'écran a à dire **sous** la liste des rondes — le CA de l'attente nommée.
 *
 * Trois états, et les trois comptent : `attente` dit **pourquoi** la ronde suivante n'est pas là
 * (sans quoi le scoreur ne distingue pas « plus rien à jouer » de « il reste à saisir ») ; `fini`
 * dit que le classement est définitif ; `null` quand la dernière ronde due est **en cours** — rien
 * à promettre, rien de terminé, se taire est la seule réponse juste.
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
 * ⚠️ **Deux listes et pas une**, et c'est la lettre du CA : une rencontre non saisie attend le
 * **scoreur de sa cible**, une rencontre saisie et non validée attend un **geste de validation**.
 * Les confondre en « il manque 3 rencontres » renvoie chercher partout (`P-3`). Une rencontre
 * **désynchronisée** est rangée à part : elle attend un rétablissement de population (ADR-0049 §4),
 * et l'annoncer « à saisir » enverrait buter sur un tir que le serveur refuse d'écraser.
 */
export interface CeQuiManque {
  aSaisir: string[]
  aValider: string[]
  /** Validées **localement**, en attente de synchronisation (`E04US009`). Personne n'a de geste à
   * faire : elles attendent le réseau. Elles ont leur propre liste au lieu d'être écartées, sinon
   * le résumé devient **vide** sous une phrase d'attente — le cul-de-sac que ce CA ferme. */
  enFile: string[]
  bloquees: string[]
}

export function ceQuiManque(rencontres: readonly RencontreSuisse[]): CeQuiManque {
  const manque: CeQuiManque = { aSaisir: [], aValider: [], enFile: [], bloquees: [] }
  for (const rencontre of rencontres) {
    const nom = nommerRencontre(rencontre)
    if (rencontre.desynchronisee) {
      manque.bloquees.push(nom)
      continue
    }
    const duel = rencontre.duel
    if (duel.validee_par !== null) continue
    // ⚠️ **Une validation en file hors-ligne a sa propre ligne** : la ranger dans `aValider`
    // faisait dire deux choses contraires à deux phrases du même écran. ⚠️ **Mais l'écarter était
    // pire** (2ᵉ passe) : `validation_en_attente` est **purement local** — seule la tablette qui a
    // mis en file le voit, l'organisateur ne voit rien —, et si c'était la dernière rencontre le
    // résumé devenait **vide** sous « la ronde suivante sera appariée quand celle-ci sera saisie et
    // validée ». Elle est donc **nommée**, avec ce qu'elle attend vraiment : le réseau.
    if (duel.validation_en_attente === true) {
      manque.enFile.push(nom)
      continue
    }
    // ⚠️ **`resultat.termine` et non `manches.length > 0`** : une rencontre à demi tirée n'est pas
    // « à valider », elle est encore à saisir. Le classement de `etatRencontre` juste au-dessus
    // fait la même lecture, et la refaire autrement ici ferait diverger deux phrases du même écran.
    if (duel.resultat?.termine === true) manque.aValider.push(nom)
    else manque.aSaisir.push(nom)
  }
  return manque
}

/** « MARTIN Jean – LE GOFF Yann », ou `?` si un côté manque (bye tardif, population mouvante).
 *
 * ⚠️ Le nom est rendu **en entier**, comme `nomDeLArcher` : la JSDoc annonçait une forme abrégée
 * (« Martin D. ») que la fonction n'a jamais produite — corrigé en revue, la fiche de recette
 * portait la même erreur au même moment. */
function nommerRencontre(rencontre: RencontreSuisse): string {
  const cote = (duelliste: Duelliste | null) =>
    duelliste === null ? '?' : `${duelliste.nom} ${duelliste.prenom}`
  return `${cote(rencontre.haut)} – ${cote(rencontre.bas)}`
}
