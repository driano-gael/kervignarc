// Lecture du code de scoreur porté par le QR (E16US015, ADR-0105) : `…/scoreur#code=<CODE>`.
//
// ⚠️ **Le fragment, pas la query** : un fragment n'est jamais envoyé au serveur — ni journal
// d'accès uvicorn, ni en-tête `Referer` —, là où un `?code=` y serait écrit à chaque scan.
// ⚠️ Forme différente du QR de cible (`…/?poste=`, à la racine) : ici le chemin nomme le monde,
// donc le routeur d'adresses (ADR-0059) aiguille seul, sans règle ajoutée à `resoudreRole`
// (ADR-0042). Isolé d'`EspaceScoreur.tsx` pour qu'il n'exporte que des composants (ESLint).

import { useSyncExternalStore } from 'react'

export function codeScoreurDepuisUrl(): string | null {
  if (typeof window === 'undefined') return null
  return new URLSearchParams(window.location.hash.slice(1)).get('code')
}

const abonnes = new Set<() => void>()

function abonner(rappel: () => void): () => void {
  abonnes.add(rappel)
  // ⚠️ **Deux écrivains, deux fils.** `abonnes` couvre l'écriture de l'application
  // (`oublierCodeScoreurUrl`) ; `hashchange` couvre celle du **navigateur** — un QR scanné alors que
  // l'onglet est déjà sur `/scoreur` est une navigation *same-document*, sans rechargement. Sans ce
  // second fil, le code n'arrivait jamais et restait dans la barre d'adresse (revue du 05/09/2026).
  // `replaceState` n'émet pas `hashchange` : aucune double notification.
  window.addEventListener('hashchange', rappel)
  return () => {
    abonnes.delete(rappel)
    window.removeEventListener('hashchange', rappel)
  }
}

// Le code d'arrivée **abonné**, pas seulement lu. ⚠️ C'est ce qui rend sa consommation
// **structurelle** : `replaceState` ne notifie personne, si bien qu'une simple lecture au rendu
// laisse l'ancienne valeur dans l'élément React déjà committé. Le trou ne se refermait alors que
// parce qu'un store voisin provoquait un rendu au bon moment — invariant que rien n'écrivait ni ne
// gardait (3ᵉ passe de revue, 05/09/2026). Même idiome que `shared/navigation/useChemin.ts`, dont
// l'instantané est le `pathname` **seul** — il ne voit donc aucun changement de fragment.
export function useCodeScoreurDArrivee(): string | null {
  return useSyncExternalStore(abonner, codeScoreurDepuisUrl, () => null)
}

// Retire `code` du fragment **sans recharger**, en laissant intacts la query et le reste du
// fragment. Appelé au shell (`App.tsx`), quel que soit le monde servi : un code refusé ne doit pas
// se rejouer au rechargement, et un code personnel n'a rien à faire dans l'historique d'une
// tablette partagée. ⚠️ **Ne pas élargir en « vider le fragment »** : `naviguer` (`useChemin.ts`)
// conserve query et fragment, donc cette fonction s'exécute aussi sur des adresses qui ne sont pas
// celles du monde scoreur.
export function oublierCodeScoreurUrl(): void {
  if (typeof window === 'undefined') return
  const fragment = new URLSearchParams(window.location.hash.slice(1))
  fragment.delete('code')
  const reste = fragment.toString()
  const adresse = window.location.pathname + window.location.search + (reste ? `#${reste}` : '')
  window.history.replaceState(null, '', adresse)
  abonnes.forEach((rappel) => rappel())
}
