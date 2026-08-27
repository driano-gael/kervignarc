// Pagination d'une liste projetée en salle — retour maquettes du 04/08/2026 (P06).
//
// ⚠️ **Ce module vivait dans `features/routage/` jusqu'à E16US009.** Il en est sorti quand une
// **deuxième** feature s'est mise à paginer (`competition`, le classement projeté) : le laisser où
// il était aurait créé une arête `competition → routage` — une dépendance entre features que rien
// ne justifie, et exactement ce que la carte du code mesure (`DETTE-083`, signal
// `features-enchevetrees`). Deux consommateurs
// réels, donc `shared/`, comme `etatRencontre` en E05US027 ; pas une abstraction sur pari.
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

import { useEffect, useState } from 'react'

/** Comment une **liste projetée** se découpe et à quel rythme elle tourne (E16US009).
 *
 * ⚠️ **Deux durées coexistent sur un écran de salle, et les confondre est le piège de cette US** :
 * `VueProgrammee.cadence_s` dit combien de temps l'écran reste sur *une vue* ; `cadence_page_s` dit
 * à quel rythme la *liste* tourne **à l'intérieur** de cette vue.
 *
 * Le type vit ici et non dans `features/ecrans/api.ts` — dont il est pourtant le miroir d'un DTO —
 * parce que ses **consommateurs** sont les deux vues paginées, dans deux features distinctes. L'y
 * laisser aurait fait importer `features/ecrans` par `features/competition` et `features/routage` :
 * deux arêtes entre features pour un type de deux entiers (cf. `DETTE-083`). */
export interface ReglagePages {
  noms_par_page: number
  cadence_page_s: number
}

/** Combien de noms par page, **à défaut de réglage**.
 *
 * *« Le maximum d'archers sur une page quand même »* — mais un maximum a une limite physique : ce
 * qu'on lit **à dix mètres**. 40 noms tiennent en trois colonnes sur un 1920x1080 en gardant une
 * hauteur de ligne lisible de loin ; au-delà, on gagne des pages et on perd la lecture, ce qui est
 * l'inverse du but.
 *
 * ✅ **`DETTE-039` résorbée par E16US009** : la valeur est désormais **réglée par écran** et servie
 * par le serveur (`Affichage.pages`), parce qu'elle dépend de la diagonale du projecteur, de la
 * distance de lecture et de la longueur des noms du club — trois propriétés du **lieu**. Ce qui
 * reste ici n'est plus le réglage mais le **défaut**, et il est volontairement identique à
 * `ReglagePages.par_defaut()` côté serveur : un écran non réglé se comporte exactement comme avant
 * l'US. Les deux valeurs doivent bouger ensemble ; `pagination.test.ts` l'épingle.
 */
export const NOMS_PAR_PAGE = 40

/** Durée d'affichage d'une page, en secondes, **à défaut de réglage**.
 * *« On peut dire que 20 s (réglable) est correct. »*
 *
 * ✅ Le « (réglable) » du questionnaire est livré par **E16US009** : la durée est attachée à la
 * configuration de l'écran, donc au serveur, et arrive par `Affichage.pages.cadence_page_s`. Ce
 * qui reste ici est le **défaut**, aligné sur `ReglagePages.par_defaut()`. */
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

/**
 * Le temps **pendant lequel une vue projetée a été affichée**, cumulé d'un passage à l'autre.
 *
 * ⚠️ **`secondes_ecoulees` est le temps d'affichage de la vue, pas l'heure du monde** (cf.
 * `pageCourante`). Une page calée sur l'heure absolue n'avance que par sauts, et quand la période
 * du déroulé et la cadence de page tombent juste, **certaines pages ne sortent jamais** — vérifié
 * en E07US008 : déroulé « affectations 30 s + classement 30 s » et trois pages → la page 2 jamais
 * projetée de la journée.
 *
 * Le cumul vit **au module** et non dans un état React : le composant est démonté chaque fois que
 * l'écran passe à une autre vue, donc tout état interne serait perdu — c'est précisément ce qu'on
 * cherche à conserver. Reste une **horloge** et non un compteur incrémenté, pour la raison écrite
 * dans `salle/rotation.ts` : un onglet en arrière-plan voit ses minuteurs bridés, et huit heures de
 * dérive figeraient l'écran.
 *
 * ⚠️ **Le compteur est indexé par `cle`, et c'est E16US009 qui l'a rendu nécessaire.** La version
 * d'origine tenait **un seul** cumul au module, sous le commentaire « une seule surface projetée
 * par onglet, donc pas de collision possible ». Ce postulat tombe dès qu'une **deuxième** vue
 * pagine : le classement et les affectations se partageaient alors le même compteur, si bien que
 * les pages du classement avançaient pendant que l'écran montrait les affectations — et
 * réciproquement. Chaque vue paginée passe donc sa propre clé.
 */
const secondesAffichees = new Map<CleDePage, number>()

/** Vide les cumuls. **RÉSERVÉ AUX TESTS** — le double tiret bas du nom n'est pas décoratif.
 *
 * Sans cette porte, les tests dépendent de leur **ordre** : `useSecondesDAffichage` écrit son cumul
 * au démontage, dans une `Map` de module partagée par tout un fichier de test, si bien qu'un test
 * qui avance l'horloge fait échouer le suivant — et le diagnostic coûte bien plus cher que la
 * fonction (relevé en 2ᵉ passe, axe D ; le besoin s'est confirmé en 3ᵉ dans un second fichier).
 *
 * ⚠️ **Ne JAMAIS l'appeler depuis du code de production.** Ce qu'elle efface est exactement ce que
 * le module protège : le cumul survit au démontage **pour que les dernières pages finissent par
 * sortir**. Un appel périodique — au rafraîchissement d'un WebSocket, sur un bouton « réinitialiser
 * l'affichage » — figerait l'écran de salle sur la page 1 toute la journée, c'est-à-dire le défaut
 * d'origine d'E07US008 restauré. Et aucun test ne le verrait : la suite passe *parce que* la
 * fonction remet à zéro. *(Le risque a été nommé par l'axe adversarial en 3ᵉ passe. L'export reste
 * — l'alternative, `vi.resetModules()` + import dynamique dans deux fichiers, coûte plus qu'elle ne
 * rapporte, règle 12 — mais le nom porte l'avertissement.)* */
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
