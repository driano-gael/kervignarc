// Garde-fou du reset global `button` (E16US010, 2ᵉ passe de revue).
//
// ⚠️ **Ce test existe parce que ni `tsc`, ni le lint, ni jsdom ne peuvent voir une couleur.**
// `App.css` porte un reset `button { background: var(--brand-surface); font-weight: 800 }` :
// toute classe qui *ressemble à du texte* mais est portée par un `<button>` doit le **désarmer**,
// sinon elle devient un pavé rouge club — 1,5:1 en thème clair.

// C'est arrivé en revue : `.badge-preparation` est passée de `<span>` à `<button>` pour être
// atteignable au doigt et a hérité de l'aplat, alors que `.archer__doublon`, écrite dans le même
// commit, désarmait le reset — le geste était connu et oublié dix lignes plus loin.

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// Les classes portées par un `<button>` alors qu'elles rendent du **texte inline**. En ajouter une
// sans la déclarer ici ne fait rien tomber : c'est la limite de ce garde-fou, et elle est dite.
const CLASSES_TEXTE_SUR_BOUTON = [
  'badge-preparation',
  'archer__doublon',
  'recherche-resultat__ouvrir',
]

const CSS = readFileSync(join(__dirname, 'App.css'), 'utf8')

function bloc(classe: string): string {
  // Le premier bloc du sélecteur nu (`.x {` et non `.x--variante` ni `button.x`).
  const debut = CSS.indexOf(`\n.${classe} {`)
  expect(debut, `bloc .${classe} introuvable`).toBeGreaterThan(-1)
  return CSS.slice(debut, CSS.indexOf('}', debut))
}

describe('reset global `button` — désarmement obligatoire', () => {
  it('le reset existe bien, et repeint le fond', () => {
    // Si ce test tombe, c'est le reset qui a changé : les suivants n'ont plus le même sens.
    expect(CSS).toMatch(/\nbutton \{[^}]*background: var\(--brand-surface\)/)
  })

  it.each(CLASSES_TEXTE_SUR_BOUTON)('.%s déclare son propre `background`', (classe) => {
    expect(bloc(classe)).toMatch(/background:/)
  })

  it.each(CLASSES_TEXTE_SUR_BOUTON)('.%s ne laisse pas la graisse 800 du reset', (classe) => {
    // `font: inherit` remet aussi la graisse ; l'un ou l'autre convient.
    expect(bloc(classe)).toMatch(/font-weight:|font: inherit/)
  })
})
