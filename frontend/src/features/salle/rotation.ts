// Rotation du déroulé d'un écran de salle (E07US004) — logique pure, aucun React, aucun DOM.
//
// Convention du projet : le JSX ne se teste pas, la logique si. Ce qui se calcule ici — *quelle vue
// à quel moment*, *combien de temps reste-t-il* — vit donc à part, et `EcranSalle.tsx` ne fait que
// rendre le résultat.
//
// **La rotation se déduit du temps écoulé, elle ne s'incrémente pas.** Un `setInterval` qui ferait
// « vue suivante » toutes les N secondes dériverait : les minuteurs de navigateur sont bridés dans
// un onglet en arrière-plan ou sur une machine en veille, et un écran de salle tourne huit heures
// d'affilée. En repartant à chaque tick d'un *temps écoulé* mesuré sur l'horloge, l'écran retrouve
// toujours la bonne vue — même après un gel de deux minutes.

import type { VueProgrammee } from '../ecrans/api'

export interface EtatRotation {
  /** Position dans la séquence — clé de rendu, et non la vue elle-même : une même vue peut figurer
   * plusieurs fois dans un déroulé (« classement, plan, classement »). */
  index: number
  vue: VueProgrammee
  /** Secondes restantes sur cette vue, pour une éventuelle jauge de progression. */
  reste_s: number
}

/**
 * La vue à afficher après `secondes_ecoulees` de déroulé, et ce qu'il lui reste.
 *
 * La séquence est jouée **en boucle** : au-delà d'un tour complet, on repart au début (modulo).
 * Rend `null` sur une séquence vide — le serveur n'en produit jamais (`SequenceVuesVide`), mais un
 * écran qui planterait sur une réponse inattendue serait la panne la plus coûteuse du dispositif :
 * personne n'est devant pour le relancer.
 */
export function vueCourante(
  vues: readonly VueProgrammee[],
  secondes_ecoulees: number,
): EtatRotation | null {
  const total = vues.reduce((somme, etape) => somme + etape.cadence_s, 0)
  if (vues.length === 0 || total <= 0) return null
  // `%` peut rendre un négatif si l'horloge recule (mise à l'heure NTP en cours de journée) : on le
  // ramène dans [0, total[ plutôt que de sortir de la séquence.
  let reste = ((secondes_ecoulees % total) + total) % total
  for (let index = 0; index < vues.length; index += 1) {
    const etape = vues[index]
    if (etape === undefined) continue
    if (reste < etape.cadence_s) {
      return { index, vue: etape, reste_s: etape.cadence_s - reste }
    }
    reste -= etape.cadence_s
  }
  // Inatteignable (la somme des cadences vaut `total`), mais rendre la première vue vaut mieux que
  // rendre `null` et éteindre l'écran sur une erreur d'arrondi.
  const premiere = vues[0]
  return premiere === undefined ? null : { index: 0, vue: premiere, reste_s: premiere.cadence_s }
}

/**
 * Le compte à rebours d'une prise de contrôle, décompté **localement**.
 *
 * `reste_initial_s` vient du serveur (`Affichage.reste_s`), `secondes_depuis` est mesuré depuis sa
 * réception. C'est ce calcul local qui rend la reprise du déroulé insensible au réseau : l'écran
 * sait quand la prise finit sans avoir à le redemander (ADR-0064).
 *
 * Rend `null` quand la prise n'a pas d'échéance — « jusqu'à ce que l'admin rende la main ».
 */
export function resteDeLaPrise(
  reste_initial_s: number | null,
  secondes_depuis: number,
): number | null {
  if (reste_initial_s === null) return null
  return Math.max(0, reste_initial_s - secondes_depuis)
}

/** « 7 min 12 s », « 45 s » — le format d'un compte à rebours lu **de loin**.
 *
 * Pas de zéros de tête ni de `:` : à dix mètres, « 7 min » se lit, « 07:12 » se déchiffre. */
export function formaterReste(secondes: number): string {
  const entier = Math.max(0, Math.round(secondes))
  if (entier < 60) return `${entier} s`
  const minutes = Math.floor(entier / 60)
  const reste = entier % 60
  return reste === 0 ? `${minutes} min` : `${minutes} min ${reste} s`
}
