// Lecture du code de cible transporté par l'URL du QR (E04US001).
//
// Le QR d'une cible (E09US008) encode l'URL de rattachement `…/?poste=<CODE>`. Ici on lit ce
// paramètre : **absent** (`null`) → la tablette n'est pas un poste (app normale) ; **présent** (même
// vide) → écran de poste. Isolé de `EspacePoste.tsx` pour que ce dernier n'exporte que des composants
// (règle ESLint `react-refresh/only-export-components`).

export function codePosteDepuisUrl(): string | null {
  if (typeof window === 'undefined') return null
  return new URLSearchParams(window.location.search).get('poste')
}

// Retire `?poste=…` de l'URL **sans recharger** (pas de routeur : `history.replaceState`). Appelé au
// **détachement** : sans ça, le paramètre survivrait et l'app réafficherait l'écran de poste (voire
// re-rattacherait automatiquement) alors que le bénévole vient de détacher la tablette.
export function oublierCodePosteUrl(): void {
  if (typeof window === 'undefined') return
  window.history.replaceState(null, '', window.location.pathname + window.location.hash)
}
