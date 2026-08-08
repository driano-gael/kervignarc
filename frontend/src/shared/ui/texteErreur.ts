import { ErreurApi } from '../api/client'

/**
 * Le **texte affichable** d'une erreur, sans son rendu — même invariant que `MessageErreur`, dont ce
 * module est le pendant sans JSX (`react-refresh` interdit d'exporter autre chose qu'un composant
 * depuis un `.tsx`).
 *
 * Extrait en E16US003 pour les rendus **ad hoc contextuels** (« … injoignable — {détail} ») que
 * DETTE-004 a explicitement laissés hors du composant générique : ils gardent leur phrase propre,
 * mais rien ne les empêchait jusqu'ici de recracher un `TypeError: Failed to fetch` en anglais à
 * l'écran — précisément le mode de panne du LAN du jour J, masqué en développement (`localhost`
 * ne coupe pas).
 *
 * ⚠️ **Ce module est le point de vérité, pas l'inventaire des sites ralliés.** E16US003 y a rallié
 * les cinq rendus de son périmètre (`Completude` ×2 — lecture *et* mutation —,
 * `CompletudeAdministrative`, `Accueil`, `FriseCycleDeVie`) ; **13 rendus bruts subsistent dans le
 * dépôt, répartis sur 8 fichiers** (décompte terrain du 08/08/2026, DETTE-050 — les fichiers à
 * occurrences multiples ne portent qu'**un** marqueur, qui annonce le compte). S'y ajoutent deux
 * **copies verbatim** de cette fonction (`duels/Duels.tsx`, `placement/Placement.tsx`) et deux
 * encodages **inline** du même invariant avec un repli propre (`supervision/Supervision.tsx`,
 * `supervision/PiloterEcrans.tsx`) : cinq sites au total portent la logique de ce module, dont un
 * seul fait autorité. C'est tracé au registre — voir `# DETTE-004` et `# DETTE-050` ci-dessous.
 * Ne pas lire l'existence de ce module comme « la déduplication est faite » : la revue d'E16US003 a
 * montré qu'un helper extrait et appliqué à moitié est plus trompeur qu'un helper absent.
 *
 * Seule une `ErreurApi` porte un message **mappé à la frontière API**, donc destiné à l'utilisateur
 * (règle 5) ; toute autre erreur est un imprévu technique et se réduit à un message générique.
 */
// DETTE-004 — résorption **partielle** : les rendus ad hoc du dépôt n'y sont pas tous ralliés.
// DETTE-050 — les 13 rendus bruts non ralliés (8 fichiers) et les 4 duplications de ce narrowing.
export function texteErreur(erreur: Error): string {
  return erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
}
