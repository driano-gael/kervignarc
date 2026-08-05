// Thème d'un poste de saisie (D-26, E04US001).
//
// Un poste peut basculer en clair/sombre selon la lumière de **sa** cible (baie vitrée vs fond de
// gymnase) sans toucher aux autres tablettes. La préférence est locale au poste (portée par le
// `sessionPosteStore`, persistée) ; ici, on ne fait que l'**appliquer** en posant `data-theme` sur
// `<html>`, ce qui active le bloc CSS correspondant.
//
// `null` = « Système ». Depuis E17US001 il pose `data-theme="systeme"` au lieu de **retirer**
// l'attribut : le défaut de l'application n'est plus « suivre l'OS » mais le **sombre de la charte**
// (`DV-02`, cf. `index.css`). Sans attribut, un poste réglé sur « Système » retomberait donc sur le
// sombre en toutes circonstances, et l'option perdrait son sens ; avec l'attribut, c'est une règle
// `@media (prefers-color-scheme: light)` dédiée qui lui rend son effet.

export type Theme = 'clair' | 'sombre'

export function appliquerTheme(theme: Theme | null): void {
  // Garde SSR / test (environnement node sans DOM), cohérente avec le `typeof window` d'`url.ts` :
  // hors navigateur il n'y a pas de `<html>` à styler, on ne fait rien.
  if (typeof document === 'undefined') return
  const racine = document.documentElement
  if (theme === null) {
    racine.dataset.theme = 'systeme'
  } else {
    racine.dataset.theme = theme === 'sombre' ? 'dark' : 'light'
  }
}
