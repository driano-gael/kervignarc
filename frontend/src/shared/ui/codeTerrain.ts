// L'alphabet des codes de terrain, et ce qu'on en fait — retour maquettes du 04/08/2026 (S01).
//
// Séparé de `PaveCode.tsx` pour la règle ESLint `react-refresh/only-export-components` (un `.tsx`
// n'exporte que des composants — même parti que `features/admin/axes.ts`), et parce que la
// normalisation est **pure**, donc testable sans rendu.
//
// ⚠️ **Duplication assumée de l'alphabet serveur.** C'est sa 3ᵉ occurrence (`infrastructure/postes/
// codes.py`, `infrastructure/scoreurs/codes.py`, ici), donc le seuil où le projet autorise à
// réfléchir à un remède structurel — mais les deux premières sont en Python et celle-ci en
// TypeScript : aucun pattern ne les réunit sans exposer l'alphabet par l'API, ce qui serait une US à
// part entière. Le garde-fou réel est ailleurs : **le serveur reste l'autorité**. Ce module est une
// aide à la frappe, pas une validation — un code refusé par le serveur reste refusé.

/** Miroir de `ALPHABET_CODE` (backend) : 32 symboles, sans les confondables `I`, `O`, `0`, `1`. */
export const ALPHABET_CODE = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

/** Miroir de `LONGUEUR_CODE` (backend) — sert à dessiner les cases et à borner la frappe, jamais à
 * décider qu'un code est bon. */
export const LONGUEUR_CODE = 6

/**
 * Ne garde d'une frappe (ou d'un collage) que ce qui peut appartenir à un code.
 *
 * Elle sert deux cas réels : le collage d'un code reçu par message (avec espaces, tirets ou
 * minuscules) et la frappe au clavier physique du PC d'organisation. Les quatre confondables sont
 * **retirés plutôt que corrigés** : traduire `O` en `0` serait une supposition, et `0` n'existe pas
 * plus que `O` dans l'alphabet — il n'y a rien vers quoi corriger.
 */
export function normaliserCode(brut: string): string {
  return [...brut.toUpperCase()]
    .filter((c) => ALPHABET_CODE.includes(c))
    .slice(0, LONGUEUR_CODE)
    .join('')
}
