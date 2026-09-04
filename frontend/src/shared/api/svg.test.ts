// Test de la construction de la data URL des QR (E11US008 cible, E16US015 scoreur) —
// logique **pure**, sans DOM ni
// réseau (patron testable du projet : extraire la logique pure et la verrouiller, cf.
// `exports/api.test.ts`). On fige le format de la data URL (préfixe + encodage) : une régression
// silencieuse casserait l'affichage du QR à l'écran.

import { describe, expect, it } from 'vitest'
import { svgEnDataUrl } from './svg'

describe('svgEnDataUrl', () => {
  it('préfixe le SVG en data URL image/svg+xml, contenu URL-encodé', () => {
    expect(svgEnDataUrl('<svg></svg>')).toBe('data:image/svg+xml,%3Csvg%3E%3C%2Fsvg%3E')
  })

  it('échappe les caractères qui refermeraient le contexte data URL (#, &, espace)', () => {
    const svg = '<svg id="a b"># &</svg>'
    const url = svgEnDataUrl(svg)

    expect(url.startsWith('data:image/svg+xml,')).toBe(true)
    // Round-trip : après décodage, le SVG est retrouvé intact — rien n'a fui hors du contexte.
    expect(decodeURIComponent(url.slice('data:image/svg+xml,'.length))).toBe(svg)
  })
})
