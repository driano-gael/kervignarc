// Lecture du code de scoreur porté par le QR (E16US015, ADR-0105) : `…/scoreur#code=<CODE>`.
//
// ⚠️ **Le fragment, pas la query** : un fragment n'est jamais envoyé au serveur — ni journal
// d'accès uvicorn, ni en-tête `Referer` —, là où un `?code=` y serait écrit à chaque scan.
// ⚠️ Forme différente du QR de cible (`…/?poste=`, à la racine) : ici le chemin nomme le monde,
// donc le routeur d'adresses (ADR-0059) aiguille seul, sans règle ajoutée à `resoudreRole`
// (ADR-0042). Isolé d'`EspaceScoreur.tsx` pour qu'il n'exporte que des composants (ESLint).

export function codeScoreurDepuisUrl(): string | null {
  if (typeof window === 'undefined') return null
  return new URLSearchParams(window.location.hash.slice(1)).get('code')
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
}
