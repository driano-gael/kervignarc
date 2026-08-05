// Pagination d'une liste de noms projetée en salle — retour maquettes du 04/08/2026 (P06).
//
// **Ceci ferme une question que le code disait ouverte.** `VueAffectations` porte cet avertissement
// depuis E07US008 : *« le volet "scannabilité" de Q-UX2 reste ouvert : 200 archers ne tiennent pas
// sur un écran projeté, et rien ici ne pagine ni ne cycle »*. Le questionnaire P06 y répond, variante
// A retenue — « défilement par pages, tri par nom », *« oui pour le compteur de pages »* — avec trois
// précisions :
//
//   · « mettre le maximum d'archers sur une page quand même » ;
//   · « grossir le compteur de page, il faut qu'il soit visible, de même que les lettres comprises
//     dans le râteau de nom » ;
//   · « on peut dire que 20 s (réglable) par écran de liste de noms est correct » ;
//   · tri **par nom** — *« c'est plus clair »* — et *« d'abord par tour, puis par archer »*.
//
// **La page se déduit du temps, elle ne s'incrémente pas** — même raisonnement que `salle/rotation.ts`
// et pour la même raison : un `setInterval` dérive dans un onglet en arrière-plan, et un écran de
// salle tourne huit heures d'affilée. On repart de l'horloge à chaque battement.

/** Combien de noms par page.
 *
 * *« Le maximum d'archers sur une page quand même »* — mais un maximum a une limite physique : ce
 * qu'on lit **à dix mètres**. 40 noms tiennent en trois colonnes sur un 1920×1080 en gardant une
 * hauteur de ligne lisible de loin ; au-delà, on gagne des pages et on perd la lecture, ce qui est
 * l'inverse du but.
 *
 * ⚠️ Valeur **à confirmer sur le vidéoprojecteur réel** : elle dépend de la diagonale, de la distance
 * et de la longueur des noms du club. Elle est isolée ici, en un seul point, pour être ajustée sans
 * relire le composant.
 */
export const NOMS_PAR_PAGE = 40

/** Durée d'affichage d'une page, en secondes. *« On peut dire que 20 s (réglable) est correct. »*
 *
 * Le « réglable » n'est **pas** livré ici : rendre la durée configurable suppose de l'attacher à la
 * configuration de l'écran, donc au serveur — hors du périmètre front de ce lot. La valeur est le
 * défaut, surchargeable par paramètre, et le réglage côté admin est programmé en US suivante. */
export const SECONDES_PAR_PAGE = 20

/** Nombre de pages nécessaires pour `total` noms. Toujours ≥ 1 : une liste vide a une page, celle
 * qui dit qu'elle est vide — rendre 0 obligerait chaque appelant à traiter le cas à part. */
export function nombreDePages(total: number, parPage = NOMS_PAR_PAGE): number {
  if (parPage <= 0) return 1
  return Math.max(1, Math.ceil(total / parPage))
}

/**
 * L'index (base 0) de la page à afficher après `secondes_ecoulees`.
 *
 * Calé sur l'**heure absolue** et non sur le temps depuis l'allumage : deux écrans voisins qui
 * affichent la même liste tournent alors ensemble, au lieu de montrer deux pages différentes à sept
 * secondes d'écart — l'effet le plus désagréable d'un mur de projection.
 */
export function pageCourante(
  nbPages: number,
  secondes_ecoulees: number,
  secondesParPage = SECONDES_PAR_PAGE,
): number {
  if (nbPages <= 1 || secondesParPage <= 0) return 0
  const cycles = Math.floor(secondes_ecoulees / secondesParPage)
  // `%` peut rendre un négatif si l'horloge recule (mise à l'heure en cours de journée) : on ramène
  // dans [0, nbPages[ plutôt que de sortir de la liste.
  return ((cycles % nbPages) + nbPages) % nbPages
}

/** La tranche de noms d'une page. Ne déborde jamais : une page hors bornes rend un tableau vide
 * plutôt que `undefined`, qu'un `.map` ferait planter sur un écran que personne ne surveille. */
export function trancheDePage<T>(lignes: readonly T[], page: number, parPage = NOMS_PAR_PAGE): T[] {
  if (parPage <= 0) return [...lignes]
  const debut = page * parPage
  return lignes.slice(debut, debut + parPage)
}

/**
 * Le **râteau de noms** d'une page : de quelle lettre à quelle lettre elle va.
 *
 * *« Grossir […] les lettres comprises dans le râteau de nom »* : c'est le repère qui permet, depuis
 * la salle, de savoir en un coup d'œil si son nom est sur cette page ou s'il faut attendre le tour
 * suivant. Sans lui, un compteur « page 3/5 » n'apprend rien à quelqu'un qui cherche « MARTIN ».
 *
 * On prend les trois premières lettres et non la seule initiale : sur un club où quarante noms
 * commencent par la même lettre, « L → L » ne distingue rien. Rend `null` sur une page vide.
 */
export function rateauDePage(noms: readonly string[]): { debut: string; fin: string } | null {
  const premier = noms[0]
  const dernier = noms[noms.length - 1]
  if (premier === undefined || dernier === undefined) return null
  const abreger = (nom: string) => nom.trim().slice(0, 3).toUpperCase()
  return { debut: abreger(premier), fin: abreger(dernier) }
}
