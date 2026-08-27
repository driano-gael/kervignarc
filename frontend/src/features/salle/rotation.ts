// Rotation du déroulé d'un écran de salle (E07US004) — logique pure, aucun React, aucun DOM.
//
// Convention du projet : le JSX ne se teste pas, la logique si. ⚠️ **La rotation se déduit du temps
// écoulé, elle ne s'incrémente pas** : un `setInterval` dériverait — les minuteurs sont bridés dans
// un onglet en arrière-plan ou sur une machine en veille, et un écran de salle tourne huit heures
// d'affilée. En repartant à chaque tick d'un temps écoulé mesuré sur l'horloge, l'écran retrouve
// toujours la bonne vue, même après un gel de deux minutes.

import type { VueEcran, VueProgrammee } from '../ecrans/api'

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

/** Le compte à rebours d'une prise de contrôle, décompté **localement**.
 *
 * `reste_initial_s` vient du serveur, `secondes_depuis` est mesuré depuis sa réception. C'est ce
 * calcul local qui rend la reprise du déroulé insensible au réseau : l'écran sait quand la prise
 * finit sans avoir à le redemander (ADR-0064). Rend `null` quand la prise n'a pas d'échéance — «
 * jusqu'à ce que l'admin rende la main ».
 */
export function resteDeLaPrise(
  reste_initial_s: number | null,
  secondes_depuis: number,
): number | null {
  if (reste_initial_s === null) return null
  return Math.max(0, reste_initial_s - secondes_depuis)
}

/** Ce que l'écran affiche à cet instant : quelle vue, et est-il encore sous contrôle.
 *
 * **Extrait du JSX en 2ᵉ passe de revue** : cette fonction porte la garantie centrale d'ADR-0064 —
 * *une prise de contrôle se termine toute seule, même sans réseau* — et elle vivait dans le rendu,
 * hors de toute épreuve. Trois cas, dont le second justifie tout le dispositif : prise en cours →
 * vue **figée** ; prise **échue** → retour à la rotation **sans rien demander au serveur**, ce qui
 * empêche un écran isolé de rester sur le podium à 18 h ; hors contrôle → rotation.
 */
export function vueAAfficher(etat: {
  sous_controle: boolean
  vue_figee: VueEcran | null
  /** Reste **local** de la prise ; `null` = pas d'échéance (« jusqu'à ce que je rende la main »). */
  reste: number | null
  rotation: EtatRotation | null
}): { vue: VueEcran | null; sous_controle: boolean } {
  const echue = etat.sous_controle && etat.reste !== null && etat.reste <= 0
  const sousControle = etat.sous_controle && !echue
  return {
    vue: (sousControle ? etat.vue_figee : null) ?? etat.rotation?.vue.vue ?? null,
    sous_controle: sousControle,
  }
}

/** Le départ à montrer sur un écran de salle : celui qu'on est **en train de tirer**.
 *
 * Le premier `lancé` (E12US008), sinon le premier encore `ouvert`. ⚠️ Si **tout est clos**, on rend
 * le **dernier** — le plus récemment terminé — et non le premier : la première version retombait
 * sur `departs[0]`, si bien qu'en fin de journée l'écran montrait le plan du départ 1, terminé
 * depuis six heures, sans rien signaler. Pur et testé : c'est une règle de choix, pas de
 * l'affichage.
 */
export function departDeSalle<T extends { etat: string }>(departs: readonly T[]): T | undefined {
  return (
    departs.find((d) => d.etat === 'lance') ??
    departs.find((d) => d.etat === 'ouvert') ??
    departs[departs.length - 1]
  )
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
