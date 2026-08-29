// Garde-fou du reset global `button` (E16US010, 2ᵉ et 3ᵉ passes de revue).
//
// ⚠️ **Ce test existe parce que ni `tsc`, ni le lint, ni jsdom ne peuvent voir une couleur.**
// `App.css` porte un reset `button { background; color; font-weight; letter-spacing; … }` :
// toute classe qui *ressemble à du texte* mais est portée par un `<button>` doit le **désarmer**,
// sinon elle hérite du chrome de marque.

// C'est arrivé en revue : `.badge-preparation` est passée de `<span>` à `<button>` pour être
// atteignable au doigt et a hérité de l'aplat rouge club, alors que `.archer__doublon`, écrite
// dans le même commit, désarmait le reset — le geste était connu et oublié dix lignes plus loin.

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// Les classes portées par un `<button>` alors qu'elles rendent du **texte inline**.
// ⚠️ Liste tenue à la main : en ajouter une sans la déclarer ici ne fait rien tomber. C'est la
// limite connue de ce garde-fou, et elle est inscrite au registre (`DETTE-094`), pas seulement dite.
const CLASSES_TEXTE_SUR_BOUTON = [
  'badge-preparation',
  'archer__doublon',
  'recherche-resultat__ouvrir',
  // Le désarmement de référence du dépôt, porté par huit boutons-texte — dont le nom du tournoi,
  // sur la ligne même où la pastille a cassé.
  'lien',
]

const CSS = readFileSync(join(__dirname, 'App.css'), 'utf8')

function bloc(classe: string): string {
  // ⚠️ **Toutes** les déclarations nues, pas la première : à spécificité égale c'est la dernière
  // qui l'emporte, et le défaut corrigé ici était précisément un doublon de bloc `.x { … }`.
  const blocs = [...CSS.matchAll(new RegExp(`\\n\\.${classe} \\{[^}]*\\}`, 'g'))].map((m) => m[0])
  expect(blocs, `bloc .${classe} introuvable`).not.toHaveLength(0)
  return blocs.join('\n')
}

describe('reset global `button` — désarmement obligatoire', () => {
  it('le reset existe bien, et repeint fond, couleur, graisse et chasse', () => {
    // Si ce test tombe, c'est le reset qui a changé : les suivants n'ont plus le même sens.
    const reset = /\nbutton \{[^}]*\}/.exec(CSS)?.[0] ?? ''
    expect(reset).toMatch(/background: var\(--brand-surface\)/)
    expect(reset).toMatch(/color: var\(--sur-brand\)/)
    expect(reset).toMatch(/font-weight: 800/)
    expect(reset).toMatch(/letter-spacing:/)
  })

  it.each(CLASSES_TEXTE_SUR_BOUTON)('.%s DÉSARME le fond de marque', (classe) => {
    // ⚠️ Pas seulement « déclare un `background` » : `background: var(--brand-surface)` passait la
    // 1ʳᵉ version de ce test **en reproduisant le bloquant à l'identique**.
    expect(bloc(classe)).toMatch(/background:\s*(none|transparent|inherit)/)
  })

  it.each(CLASSES_TEXTE_SUR_BOUTON)('.%s ne laisse pas la graisse 800 du reset', (classe) => {
    // `font: inherit` remet aussi la graisse ; l'un ou l'autre convient.
    expect(bloc(classe)).toMatch(/font-weight:|font: inherit/)
  })

  it.each(CLASSES_TEXTE_SUR_BOUTON)('.%s redéclare sa `color`', (classe) => {
    // ⚠️ **Le pire des quatre.** Le reset pose `color: var(--sur-brand)` = `#ffffff` dans les trois
    // thèmes, et `--surface-0` vaut aussi `#ffffff` en clair : sans redéclaration, c'est du blanc
    // sur blanc (1:1), pire que le 1,5:1 qui a motivé ce fichier.
    expect(bloc(classe)).toMatch(/color:/)
  })

  it.each(CLASSES_TEXTE_SUR_BOUTON)('.%s remet une chasse de texte', (classe) => {
    // ⚠️ `letter-spacing` **n'appartient pas** au raccourci `font` : `font: inherit` ne le remet
    // pas. Le reset pose `0.02em`, une chasse de bouton sur du texte de ligne.
    expect(bloc(classe)).toMatch(/letter-spacing:/)
  })
})
