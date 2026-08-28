// Pagination d'une liste projetée en salle. Décision : ADR-0098. CA : stories/E16 (P06, P07).
//
// ⚠️ **Ce module doit rester dans `shared/`** : ses deux consommateurs sont dans des features
// distinctes, et le redescendre dans l'une créerait une arête d'enchevêtrement (`DETTE-083`). ⚠️
// **La page se déduit du temps, elle ne s'incrémente pas** : un `setInterval` dérive dans un onglet
// en arrière-plan, et un écran de salle tourne huit heures d'affilée.

import { useEffect, useState } from 'react'

/** Comment une **liste projetée** se découpe et à quel rythme elle tourne. Miroir de
 * `ReglagePagesDTO` ; `features/ecrans/api.ts` le ré-exporte.
 *
 * ⚠️ **Deux « cadences » coexistent sur un écran de salle** : `VueProgrammee.cadence_s` est le temps
 * passé sur *une vue* ; `cadence_page_s` le rythme de la *liste* **à l'intérieur** de cette vue.
 * Rien n'exige que l'une divise l'autre. */
export interface ReglagePages {
  noms_par_page: number
  cadence_page_s: number
}

/** Le **défaut** appliqué à un écran non réglé — le réglage, lui, vient du serveur.
 *
 * ⚠️ **Doit rester identique à `ReglagePages.par_defaut()` côté domaine** : sinon le même écran
 * s'afficherait différemment selon qu'il a reçu sa configuration ou non, et personne dans la salle
 * ne pourrait le diagnostiquer. `pagination.test.ts` et `test_domain_ecran.py` épinglent chacun leur
 * côté — garde-fou de lecture, pas de compilation. */
export const NOMS_PAR_PAGE = 40

/** Idem, pour la durée d'affichage d'une page. Même contrainte d'égalité avec le domaine. */
export const SECONDES_PAR_PAGE = 20

/** Nombre de pages nécessaires pour `total` noms. Toujours ≥ 1 : une liste vide a une page, celle
 * qui dit qu'elle est vide — rendre 0 obligerait chaque appelant à traiter le cas à part. */
export function nombreDePages(total: number, parPage = NOMS_PAR_PAGE): number {
  if (parPage <= 0) return 1
  return Math.max(1, Math.ceil(total / parPage))
}

/** L'index (base 0) de la page à afficher après `secondes_ecoulees`.
 *
 * ⚠️ **`secondes_ecoulees` est le temps d'affichage de la vue, pas l'heure du monde.** Une première
 * version passait `Date.now()` nu, par analogie avec `salle/rotation.ts` — fausse d'un cran : la
 * rotation tourne en continu, cette vue n'est à l'écran qu'une étape sur N. Une page calée sur
 * l'heure absolue n'avançait que par sauts, et **certaines pages ne sortaient jamais** (vérifié).
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

/** Le **râteau de noms** d'une page : de quelle lettre à quelle lettre elle va — le repère qui
 * répond, depuis la salle, à « mon nom est-il sur cette page ».
 *
 * Trois lettres et non la seule initiale : sur un club où quarante noms commencent par la même,
 * « L → L » ne distingue rien. Rend `null` sur une page vide. */
export function rateauDePage(noms: readonly string[]): { debut: string; fin: string } | null {
  const premier = noms[0]
  const dernier = noms[noms.length - 1]
  if (premier === undefined || dernier === undefined) return null
  const abreger = (nom: string) => nom.trim().slice(0, 3).toUpperCase()
  return { debut: abreger(premier), fin: abreger(dernier) }
}

/** Le temps pendant lequel une vue projetée a été affichée, **cumulé d'un passage à l'autre**.
 *
 * Trois contraintes, aucune déductible du code : c'est le temps d'**affichage de la vue**, pas
 * l'heure du monde (sinon certaines pages ne sortent **jamais**) ; le cumul vit **au module**, le
 * composant étant démonté à chaque bascule de vue ; il est **indexé par vue** — partagé, il faisait
 * avancer les pages du classement pendant que l'écran montrait les affectations.
 */
const secondesAffichees = new Map<CleDePage, number>()

/** Vide les cumuls. **RÉSERVÉ AUX TESTS** — sans quoi ils dépendent de leur ordre d'exécution.
 *
 * ⚠️ **Ne JAMAIS l'appeler depuis du code de production** : elle efface exactement ce que le module
 * protège. Un appel périodique figerait l'écran de salle sur la page 1 toute la journée — et aucun
 * test ne le verrait, la suite passant *parce que* la fonction remet à zéro. */
export function __reinitialiserCumulsDePage_TESTS(): void {
  secondesAffichees.clear()
}

/** Les vues projetées qui paginent, **énumérées** plutôt que nommées par une chaîne libre.
 *
 * ⚠️ **Ce que le type ferme, et ce qu'il ne ferme pas** : il refuse une clé **inventée**, pas une
 * clé **réemployée** — `'classement'` reste légale, qu'un copier-coller peut poser ailleurs.
 * L'union ne porte **que des clés de production** : un membre `'test'` aurait rouvert la chaîne
 * libre que ce type ferme. Les tests isolent leurs cumuls par `reinitialiserCumulsDePage()`.
 */
export type CleDePage = 'classement' | 'affectations'

/** ⚠️ **`cle` est lue au montage pour l'état initial, et suivie ensuite par l'effet seul.**
 *
 * Un appelant qui changerait de clé **sans démonter** repartirait du cumul de la vue précédente.
 * Les tests isolent leurs cumuls par `__reinitialiserCumulsDePage_TESTS()`.
 * Aucun ne le fait aujourd'hui, et la parade est chez l'appelant : un `key={cle}` force le
 * remontage. *(Resynchroniser l'état en tête d'effet est un `setState` synchrone que
 * `react-hooks/set-state-in-effect` refuse, à raison : un rendu en cascade pour un cas inatteint.)*
 */
export function useSecondesDAffichage(cle: CleDePage): number {
  const [ecoulees, setEcoulees] = useState(() => secondesAffichees.get(cle) ?? 0)
  useEffect(() => {
    const debut = Date.now() / 1000
    const acquis = secondesAffichees.get(cle) ?? 0
    const battement = window.setInterval(
      () => setEcoulees(acquis + (Date.now() / 1000 - debut)),
      1000,
    )
    return () => {
      window.clearInterval(battement)
      secondesAffichees.set(cle, acquis + (Date.now() / 1000 - debut))
    }
  }, [cle])
  return ecoulees
}
