// Abonnement à l'historique du navigateur (E14US003) — la seule partie du routeur qui touche au DOM.
//
// Volontairement **mince** : toutes les décisions vivent dans `routeur.ts`, qui est pur et testé. Ici
// il n'y a que de la plomberie — pousser une entrée d'historique et prévenir React.
//
// `useSyncExternalStore` plutôt qu'un `useState` + `useEffect` : c'est l'API prévue pour lire une
// source **extérieure** à React (ici `window.location`). Elle évite le piège classique du routeur
// maison — un état local qui se désynchronise du navigateur quand l'utilisateur clique sur
// « précédent », parce que `popstate` arrive après le rendu.

import { useSyncExternalStore } from 'react'

const abonnes = new Set<() => void>()

function prevenir(): void {
  for (const abonne of abonnes) abonne()
}

/**
 * Navigue vers `chemin` sans recharger la page.
 *
 * `remplacer` écrase l'entrée courante au lieu d'en empiler une : à utiliser pour les redirections
 * **subies** (l'app corrige l'adresse elle-même), sinon le bouton « précédent » renverrait sur
 * l'adresse que l'app vient de refuser — et boucler ainsi est le défaut le plus pénible d'un routeur.
 */
export function naviguer(chemin: string, options?: { remplacer?: boolean }): void {
  if (typeof window === 'undefined') return
  // La query (`?poste=<code>` du QR) et le fragment sont **conservés** : le rattachement automatique
  // d'une tablette en dépend, et une redirection interne ne doit pas les faire disparaître.
  const complet = chemin + window.location.search + window.location.hash
  if (complet === window.location.pathname + window.location.search + window.location.hash) return
  if (options?.remplacer) window.history.replaceState(null, '', complet)
  else window.history.pushState(null, '', complet)
  prevenir()
}

function abonner(surChangement: () => void): () => void {
  abonnes.add(surChangement)
  window.addEventListener('popstate', surChangement)
  return () => {
    abonnes.delete(surChangement)
    window.removeEventListener('popstate', surChangement)
  }
}

function instantane(): string {
  return window.location.pathname
}

// Rendu hors navigateur (tests unitaires sans DOM) : la racine, donc l'écran de choix.
function instantaneServeur(): string {
  return '/'
}

/** Le chemin courant, re-rendu à chaque navigation — y compris « précédent » / « suivant ». */
export function useChemin(): string {
  return useSyncExternalStore(abonner, instantane, instantaneServeur)
}
