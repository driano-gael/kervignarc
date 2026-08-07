import { ErreurApi } from '../api/client'

/**
 * Le **texte affichable** d'une erreur, sans son rendu — même invariant que `MessageErreur`, dont ce
 * module est le pendant sans JSX (`react-refresh` interdit d'exporter autre chose qu'un composant
 * depuis un `.tsx`).
 *
 * Extrait en E16US003 pour les rendus **ad hoc contextuels** (« … injoignable — {détail} ») que
 * DETTE-004 a explicitement laissés hors du composant générique : ils gardent leur phrase propre,
 * mais rien ne les empêchait jusqu'ici de recracher un `TypeError: Failed to fetch` en anglais à
 * l'écran — précisément le mode de panne du LAN du jour J, masqué en développement. Trois sites
 * partagent cette forme (`Completude`, `CompletudeAdministrative`, `Accueil`) : le narrowing vit
 * donc **ici**, avec l'invariant qu'il sert, et n'est pas recopié trois fois.
 *
 * Seule une `ErreurApi` porte un message **mappé à la frontière API**, donc destiné à l'utilisateur
 * (règle 5) ; toute autre erreur est un imprévu technique et se réduit à un message générique.
 */
export function texteErreur(erreur: Error): string {
  return erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
}
