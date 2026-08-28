// Thème d'un poste de saisie (D-26, E04US001).
//
// Un poste bascule en clair/sombre selon la lumière de **sa** cible, sans toucher aux autres. La
// préférence est locale et persistée ; ici on ne fait que l'**appliquer** via `data-theme`. ⚠️
// Trois valeurs **et** `null`, et la distinction est le cœur du sujet : `null` = jamais choisi ⇒
// **sombre**, défaut de la charte (`DV-02`) ; `'systeme'` = le poste a **choisi** de suivre l'OS,
// effet rendu en CSS et non en JS ; `'clair'`/`'sombre'` = surcharge explicite. Confondre les deux
// premiers, c'est livrer « suivre l'OS par défaut » en croyant livrer l'inverse.

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
