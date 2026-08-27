import { ErreurApi } from '../api/client'

/**
 * Le **texte affichable** d'une erreur, sans son rendu — pendant sans JSX de `MessageErreur`.
 *
 * ⚠️ **Ce module est le point de vérité, pas l'inventaire des sites ralliés** : 13 rendus bruts
 * subsistent sur 8 fichiers, plus quatre duplications de ce narrowing. Un helper extrait et
 * appliqué à moitié est plus trompeur qu'un helper absent. Seule une `ErreurApi` porte un message
 * destiné à l'utilisateur (règle 5) ; toute autre erreur se réduit au message générique.
 */

// DETTE-004 — résorption **partielle** : les rendus ad hoc du dépôt n'y sont pas tous ralliés.
// DETTE-050 — les 13 rendus bruts non ralliés (8 fichiers) et les 4 duplications de ce narrowing.
export function texteErreur(erreur: Error): string {
  return erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
}
