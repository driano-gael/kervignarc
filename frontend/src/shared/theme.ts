// Thème d'un poste de saisie (D-26, E04US001).
//
// Un poste peut basculer en clair/sombre selon la lumière de **sa** cible (baie vitrée vs fond de
// gymnase) sans toucher aux autres tablettes. La préférence est locale au poste (portée par le
// `sessionPosteStore`, persistée) ; ici, on ne fait que l'**appliquer** en posant `data-theme` sur
// `<html>`, ce qui active le bloc CSS correspondant.
//
// Trois valeurs explicites **et** `null`, et la distinction est le cœur du sujet :
//   - `null`      = le poste n'a **jamais** choisi ⇒ **sombre**, le défaut de la charte (`DV-02`) ;
//   - `'systeme'` = le poste a **choisi** de suivre l'OS (`D-26`) ⇒ `data-theme="systeme"`, auquel une
//                   règle `@media (prefers-color-scheme: light)` dédiée rend son effet, en CSS et non
//                   en JS — la page suit alors le basculement de l'OS en direct ;
//   - `'clair'` / `'sombre'` = surcharge explicite du poste.
// Confondre les deux premiers, c'est livrer « suivre l'OS par défaut » en croyant livrer l'inverse.

export type Theme = 'clair' | 'sombre' | 'systeme'

export function appliquerTheme(theme: Theme | null): void {
  // Garde SSR / test (environnement node sans DOM), cohérente avec le `typeof window` d'`url.ts` :
  // hors navigateur il n'y a pas de `<html>` à styler, on ne fait rien.
  if (typeof document === 'undefined') return
  const racine = document.documentElement
  // `null` = **aucun choix** ⇒ le défaut de la charte, le sombre. Surtout pas « suivre l'OS » : c'est
  // l'alternative qu'ADR-0074 déclare rejeter, et elle était **livrée quand même** — `null` servait à
  // la fois de « jamais choisi » et de « Système », et le store initialise à `null`. Une tablette
  // neuve sous OS clair ouvrait donc l'application en clair. Corrigé à la revue d'E17US001.
  racine.dataset.theme = theme === 'systeme' ? 'systeme' : theme === 'clair' ? 'light' : 'dark'
}
