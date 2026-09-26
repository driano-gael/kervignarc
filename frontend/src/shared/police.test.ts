// Garde-fou de la police embarquée (E17US005, `DV-07`, ADR-0116) : l'application affiche Inter
// sur un poste sans réseau et sans la police installée. Lecture des sources sur disque, comme
// `charte.test.ts` ; racine d'exécution `frontend/` (celle de `ci.yml`).

/// <reference types="node" />
import { createHash } from 'node:crypto'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const FRONT = process.cwd()
const RACINE = join(FRONT, 'src')
const INDEX = join(RACINE, 'index.css')
const PLANCHES = join(FRONT, '..', 'maquettes', 'assets', 'systeme.css')
const REGISTRE = join(FRONT, '..', 'docs', 'dependances.md')

function fichiers(dossier: string, motif: RegExp): [string, string][] {
  return readdirSync(dossier, { withFileTypes: true }).flatMap((entree): [string, string][] => {
    const chemin = join(dossier, entree.name)
    if (entree.isDirectory()) return fichiers(chemin, motif)
    if (!motif.test(entree.name) || /\.test\.tsx?$/.test(entree.name)) return []
    return [[chemin, readFileSync(chemin, 'utf8')]]
  })
}

const sources = (): [string, string][] => fichiers(RACINE, /\.(css|tsx?)$/)

function regleInter(css: string): string[] {
  return [...css.matchAll(/@font-face\s*\{([^}]*)\}/g)]
    .map((m) => m[1] ?? '')
    .filter((corps) => /font-family:\s*['"]?Inter['"]?\s*;/.test(corps))
}

function fichierDe(regle: string, feuille: string): string {
  const src = /src:\s*url\(['"]?([^'")]+)['"]?\)\s*format\(['"]woff2['"]\)/.exec(regle)
  return resolve(dirname(feuille), src?.[1] ?? '')
}

function plage(regle: string): [number, number] {
  const m = /font-weight:\s*(\d+)\s+(\d+)\s*;/.exec(regle)
  return [Number(m?.[1] ?? Number.NaN), Number(m?.[2] ?? Number.NaN)]
}

describe('police embarquée', () => {
  const regles = regleInter(readFileSync(INDEX, 'utf8'))
  const regle = regles[0] ?? ''
  const police = fichierDe(regle, INDEX)

  it('déclare Inter depuis un fichier du dépôt, qui existe, licence à côté', () => {
    expect(regles).toHaveLength(1)
    expect(regle).toMatch(/url\(['"]?\.\.?\//)
    expect(existsSync(police)).toBe(true)
    expect(existsSync(join(dirname(police), 'OFL.txt'))).toBe(true)
  })

  it('porte l’empreinte déclarée au registre des dépendances', () => {
    // Un fichier remplacé sans sa ligne (ou une version statique glissée sous le même nom)
    // rompt la provenance déclarée : l'actif n'a ni manifeste ni lockfile pour le dire.
    const empreinte = createHash('sha256').update(readFileSync(police)).digest('hex')
    expect(readFileSync(REGISTRE, 'utf8')).toContain(empreinte)
  })

  it('couvre toutes les graisses employées par le front', () => {
    const [min, max] = plage(regle)
    const motifs = [
      /font-?[wW]eight:\s*['"]?(\d{3,4})\b/g,
      /fontWeight=\{?['"]?(\d{3,4})\b/g,
      /\bfont:\s*(?:(?:italic|normal)\s+)?(\d{3,4})\s/g,
    ]
    const employees = sources().flatMap(([, texte]) =>
      motifs.flatMap((motif) => [...texte.matchAll(motif)].map((m) => Number(m[1]))),
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
    // Un CDN échoue en silence dans le gymnase, sans internet. `index.html` d'abord : c'est là
    // qu'on colle un `<link>` de police.
    const pages: [string, string][] = [
      [join(FRONT, 'index.html'), readFileSync(join(FRONT, 'index.html'), 'utf8')],
      ...fichiers(join(FRONT, 'public'), /\.(svg|html|css|json|webmanifest)$/),
    ]
    const fautifs = [...sources(), ...pages]
      .filter(([, texte]) =>
        /((@import|url\()\s*['"]?|(href|src)=\s*['"])(https?:)?\/\//.test(texte),
      )
      .map(([chemin]) => chemin)
    expect(fautifs).toEqual([])
  })

  it('les planches lisent le même fichier, sur la même plage', () => {
    // Un renommage casserait les planches en silence : elles retomberaient sur la police système.
    const [planche] = regleInter(readFileSync(PLANCHES, 'utf8'))
    expect(planche).toBeDefined()
    expect(fichierDe(planche ?? '', PLANCHES)).toBe(police)
    expect(plage(planche ?? '')).toEqual(plage(regle))
  })
})
