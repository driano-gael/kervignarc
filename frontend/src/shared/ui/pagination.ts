// Pagination d'une liste projetée en salle. Décision : ADR-0098. CA : stories/E16 (P06, P07).
//
// ⚠️ **Ce module doit rester dans `shared/`** : ses deux consommateurs sont dans des features
// distinctes (`competition`, `routage`), et le redescendre dans l'une créerait une arête
// d'enchevêtrement que la carte du code mesure (`DETTE-083`).
//
// ⚠️ **La page se déduit du temps, elle ne s'incrémente pas.** Un `setInterval` dérive dans un
// onglet en arrière-plan, et un écran de salle tourne huit heures d'affilée : on repart de
// l'horloge à chaque battement (même parti que `salle/rotation.ts`).

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

/**
 * L'index (base 0) de la page à afficher après `secondes_ecoulees`.
 *
 * ⚠️ **`secondes_ecoulees` est le temps d'affichage de la vue, pas l'heure du monde.** Une première
 * version passait `Date.now()` nu, par analogie avec la rotation des vues de `salle/rotation.ts` —
 * l'analogie était fausse d'un cran : la rotation tourne en continu, cette vue non, elle n'est à
 * l'écran qu'une étape sur N du déroulé. Une page calée sur l'heure absolue n'avançait donc que par
 * sauts, et quand la période du déroulé et la cadence de page tombaient juste, **certaines pages ne
 * sortaient jamais** (vérifié : déroulé « affectations 30 s + classement 30 s », trois pages → la
 * page 2 jamais projetée de la journée). L'appelant fournit désormais le temps **cumulé
 * d'affichage** ; cf. `useSecondesDAffichage`, plus bas dans ce module.
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
 * Trois contraintes, dont aucune n'est déductible du code :
 * - c'est le temps d'**affichage de la vue**, pas l'heure du monde — une page calée sur l'horloge
 *   absolue n'avance que par sauts, et certaines pages ne sortent alors **jamais** de la journée ;
 * - le cumul vit **au module**, parce que le composant est démonté à chaque bascule de vue : un
 *   état React serait perdu, or c'est précisément ce qu'on veut conserver ;
 * - il est **indexé par vue** : partagé, il faisait avancer les pages du classement pendant que
 *   l'écran montrait les affectations. */
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
 * ⚠️ **Ce que le type ferme, et ce qu'il ne ferme pas** — la première rédaction promettait trop
 * (relevé par trois axes en 2ᵉ passe). Il refuse à la compilation une clé **inventée** (`'clasement'`,
 * `'palmares'`) ; il ne peut rien contre une clé **réemployée** — `'classement'` reste une valeur
 * légale, qu'un copier-coller peut poser dans une troisième vue. Fermer le réemploi demanderait une
 * clé dérivée du composant, ce qui est un autre sujet.
 *
 * L'union ne porte **que des clés de production** : y ajouter un membre `'test'` aurait rouvert, pour
 * de vrai, la chaîne libre que ce type existe pour fermer — n'importe quel composant aurait pu la
 * prendre. Les tests isolent leurs cumuls par `reinitialiserCumulsDePage()`. */
export type CleDePage = 'classement' | 'affectations'

/** ⚠️ **`cle` est lue au montage pour l'état initial, et suivie ensuite par l'effet seul.**
 *
 * Un appelant qui changerait de clé **sans démonter** repartirait donc du cumul de la vue
 * précédente. Aucun ne le fait aujourd'hui — les deux clés sont des littéraux, dans deux composants
 * distincts, et l'écran de salle démonte la vue à chaque bascule —, et la parade est chez
 * l'appelant : un `key={cle}` force le remontage.
 *
 * *(Une revue a suggéré de resynchroniser l'état en tête d'effet ; c'est un `setState` synchrone
 * dans un effet, que `react-hooks/set-state-in-effect` refuse — à raison : il déclenche un rendu en
 * cascade pour un cas que personne n'atteint. La note vaut mieux que le correctif.)* */
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
