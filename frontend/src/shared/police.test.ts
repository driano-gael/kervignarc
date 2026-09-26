// Garde-fou de la police embarquée (E17US005, `DV-07`) : l'application affiche Inter sur un poste
// sans réseau et sans la police installée. Lecture des sources sur disque, comme `charte.test.ts`.

/// <reference types="node" />
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const RACINE = join(process.cwd(), 'src')
const INDEX = join(RACINE, 'index.css')

function sources(dossier: string): [string, string][] {
  return readdirSync(dossier, { withFileTypes: true }).flatMap((entree): [string, string][] => {
    const chemin = join(dossier, entree.name)
    if (entree.isDirectory()) return sources(chemin)
    if (!/\.(css|tsx?)$/.test(entree.name) || /\.test\.tsx?$/.test(entree.name)) return []
    return [[chemin, readFileSync(chemin, 'utf8')]]
  })
}

function reglesInter(css: string): string[] {
  return [...css.matchAll(/@font-face\s*\{([^}]*)\}/g)]
    .map((m) => m[1] ?? '')
    .filter((corps) => /font-family:\s*['"]?Inter['"]?\s*;/.test(corps))
}

describe('police embarquée', () => {
  const regles = reglesInter(readFileSync(INDEX, 'utf8'))
  const regle = regles[0] ?? ''

  it('déclare Inter depuis un fichier du dépôt, qui existe', () => {
    expect(regles).toHaveLength(1)
    const src = /src:\s*url\(['"]?([^'")]+)['"]?\)\s*format\(['"]woff2['"]\)/.exec(regle)
    const url = src?.[1] ?? ''
    expect(url).toMatch(/^\.\.?\//)
    const fichier = resolve(dirname(INDEX), url)
    expect(existsSync(fichier)).toBe(true)
    // OFL 1.1 : la licence voyage avec le fichier (règle 11).
    expect(existsSync(join(dirname(fichier), 'OFL.txt'))).toBe(true)
  })

  it('couvre toutes les graisses employées par le front', () => {
    // ⚠️ Une graisse hors plage est rendue par la plus proche disponible, sans erreur visible.
    const plage = /font-weight:\s*(\d+)\s+(\d+)\s*;/.exec(regle)
    const min = Number(plage?.[1] ?? Number.NaN)
    const max = Number(plage?.[2] ?? Number.NaN)
    const employees = sources(RACINE).flatMap(([, texte]) =>
      [...texte.matchAll(/font-?[wW]eight:\s*['"]?(\d{3})/g)].map((m) => Number(m[1])),
    )
    expect(employees.length).toBeGreaterThan(0)
    for (const graisse of employees) {
      expect(graisse).toBeGreaterThanOrEqual(min)
      expect(graisse).toBeLessThanOrEqual(max)
    }
  })

  it("n'attend pas la police pour afficher le texte", () => {
    expect(regle).toMatch(/font-display:\s*swap\s*;/)
  })

  it('ne charge aucune ressource depuis un domaine externe', () => {
    // Un CDN échoue en silence dans le gymnase, sans internet : c'est la panne que l'US ferme.
    const fautifs = sources(RACINE)
      .filter(([, texte]) => /(@import|url\()\s*['"]?(https?:)?\/\//.test(texte))
      .map(([chemin]) => chemin)
    expect(fautifs).toEqual([])
  })
})
