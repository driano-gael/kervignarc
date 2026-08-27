// L'alphabet des codes de terrain, et ce qu'on en fait — retour maquettes du 04/08/2026 (S01).
//
// Séparé de `PaveCode.tsx` pour `react-refresh/only-export-components`, et parce que la
// normalisation est **pure**, donc testable sans rendu. ⚠️ **Duplication assumée de l'alphabet
// serveur** — 3ᵉ occurrence, donc le seuil du remède structurel, mais les deux premières sont en
// Python et celle-ci en TypeScript : aucun pattern ne les réunit sans exposer l'alphabet par l'API.
// Le garde-fou réel est que **le serveur reste l'autorité** ; ceci est une aide à la frappe.

/** Miroir de `ALPHABET_CODE` (backend) : 32 symboles, sans les confondables `I`, `O`, `0`, `1`. */
// DETTE-040 — 3ᵉ exemplaire (les deux autres sont en Python). Aucun remède : cf. registre.
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
