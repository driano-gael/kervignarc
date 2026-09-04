// Lecture du code de scoreur transporté par l'URL du QR (E16US015).
//
// Le QR d'un scoreur encode `…/scoreur?code=<CODE>`. ⚠️ **Forme différente du QR de cible**
// (`…/?poste=<CODE>`, racine) : ici le **chemin** nomme le monde, si bien que le routeur d'adresses
// (ADR-0059) aiguille seul — aucune règle ajoutée à `resoudreRole`, cœur risqué de l'entrée
// (ADR-0042). Isolé de `EspaceScoreur.tsx` pour que ce dernier n'exporte que des composants
// (règle ESLint `react-refresh/only-export-components`), comme `features/poste/url.ts`.

export function codeScoreurDepuisUrl(): string | null {
  if (typeof window === 'undefined') return null
  return new URLSearchParams(window.location.search).get('code')
}

// Retire `?code=…` de l'URL **sans recharger** (`history.replaceState`, pas de routeur). Appelé
// AVANT la tentative de connexion : un code refusé ne doit pas se rejouer à chaque rechargement, et
// un code personnel n'a rien à faire dans la barre d'adresse ni dans l'historique du navigateur.
export function oublierCodeScoreurUrl(): void {
  if (typeof window === 'undefined') return
  window.history.replaceState(null, '', window.location.pathname + window.location.hash)
}
