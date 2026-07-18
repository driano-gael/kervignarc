// Thème d'un poste de saisie (D-26, E04US001).
//
// Un poste peut basculer en clair/sombre selon la lumière de **sa** cible (baie vitrée vs fond de
// gymnase) sans toucher aux autres tablettes. La préférence est locale au poste (portée par le
// `sessionPosteStore`, persistée) ; ici, on ne fait que l'**appliquer** en posant `data-theme` sur
// `<html>`, ce qui active le bloc CSS correspondant (miroir de `@media (prefers-color-scheme)`).
// `null` = suivre le système (aucun `data-theme`), le comportement par défaut de l'app.

export type Theme = 'clair' | 'sombre'

export function appliquerTheme(theme: Theme | null): void {
  // Garde SSR / test (environnement node sans DOM), cohérente avec le `typeof window` d'`url.ts` :
  // hors navigateur il n'y a pas de `<html>` à styler, on ne fait rien.
  if (typeof document === 'undefined') return
  const racine = document.documentElement
  if (theme === null) {
    delete racine.dataset.theme
  } else {
    racine.dataset.theme = theme === 'sombre' ? 'dark' : 'light'
  }
}
