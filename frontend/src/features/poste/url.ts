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
