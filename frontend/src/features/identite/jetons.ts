// La traduction d'une identité en **jetons CSS** (E16US006) — fonction pure, hors composant.
//
// Dans son propre module et non dans `HabillageIdentite.tsx` : un `.tsx` n'exporte que des
// composants (convention du dépôt, cf. `features/poste/url.ts` et `features/admin/axes.ts`), et
// cette fonction est **pure**, donc testable sans rendu. C'est là que vivent les décisions ; le
// composant n'en fait que l'application.

import type { Identite, JetonsDeMarque } from './api'

/** Les trois déclinaisons de thème d'une identité, en CSS — pure, testée sans DOM.
 *
 * ⚠️ **Seuls les jetons de MARQUE sont émis.** Les neutres (`--surface-*`, `--text*`, `--border*`)
 * et les sémantiques (`--danger`, `--success`, `--info`) n'apparaissent nulle part ici : c'est le
 * verrou de `DV-06` — « 3 strates, marque personnalisable, sémantique et structure figées ». Un
 * tournoi ne redéfinit pas ce que « hors ligne » veut dire, et repeindre `--surface-0`
 * invaliderait les vingt ratios mesurés contre lui. `charte.test.ts` le vérifie.
 */
export function cssDesJetons(marqueur: string, identite: Identite): string {
  const porte = `[data-identite='${marqueur}']`
  const sombre = declaration(identite.primaire.sombre, identite.secondaire.sombre)
  const clair = declaration(identite.primaire.clair, identite.secondaire.clair)

  // Les trois mêmes sélecteurs que `index.css`, dans le même ordre et pour la même raison : le
  // sombre est le défaut (`DV-02`), le clair est un choix explicite du poste, et « Système » ne
  // bascule que sur la préférence de l'OS (`D-26`). En omettre un laisserait la surface hériter des
  // jetons du club sur ce thème-là — un tournoi à moitié habillé, sans erreur visible.
  return [
    `${porte}{${sombre}}`,
    `:root[data-theme='light'] ${porte}{${clair}}`,
    `@media(prefers-color-scheme:light){:root[data-theme='systeme'] ${porte}{${clair}}}`,
  ].join('')
}

// DETTE-087 (docs/dette.md) : les quatre jetons `--brand-2-*` sont dérivés et émis, mais **aucune
// feuille de style ne les consomme** hors des vignettes d'aperçu. Décider ce que peint l'accent
// secondaire est un choix de mise en page qu'aucune des 36 planches ne porte : l'inventer aurait
// été du design fait en douce dans une US d'implémentation. La résorption est une **question** au
// commanditaire, pas un chantier — et « on n'en veut pas » est une réponse valide, auquel cas ces
// quatre lignes se retirent.
/** Les huit jetons d'un thème : quatre pour chaque accent. */
function declaration(primaire: JetonsDeMarque, secondaire: JetonsDeMarque): string {
  return [
    `--brand-surface:${primaire.surface}`,
    `--brand-border:${primaire.contour}`,
    `--brand-text:${primaire.texte}`,
    `--sur-brand:${primaire.encre}`,
    `--brand-2-surface:${secondaire.surface}`,
    `--brand-2-border:${secondaire.contour}`,
    `--brand-2-text:${secondaire.texte}`,
    `--sur-brand-2:${secondaire.encre}`,
  ].join(';')
}
