/// <reference types="node" />

// Garde-fou d'E17US010 — la navigation des maquettes suit celle du produit.
//
// `maquettes/assets/appareils.js` transcrit l'ossature d'`axes.ts` **à la main** : chaque US qui
// ajoute, renomme ou déplace une destination la désynchronise en silence, et on relit alors des
// planches décrivant une application qui n'existe plus. Le produit est lu par **import**, jamais
// par regex — un seul des deux côtés est parsé, donc un seul peut mentir sur sa propre forme.

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { AXES, AXE_PAR_DESTINATION } from './axes'
import type { Axe } from './axes'

// `process.cwd()` est la racine du projet Vite (`frontend/`) et non ce répertoire : même parti que
// `commentaires.test.ts`, dont l'en-tête dit pourquoi `import.meta.url` ne convient pas ici.
const APPAREILS = join(process.cwd(), '..', 'maquettes', 'assets', 'appareils.js')

// ⚠️ Ces motifs épousent la forme d'`appareils.js` — un couple `['id', 'Libellé']` par ligne. Un
// reformatage du fichier les met en défaut, mais **en rouge** : plus rien n'est reconnu, donc tout
// est déclaré manquant. Le test « forme reconnue » convertit ce rouge obscur en message explicite.
const SECTION = /^\s*([a-z]+):\s*\[\s*$/
const FERMETURE = /^\s*\],?\s*$/
const COUPLE = /^\s*\['([a-z-]+)',\s*'(.+)'\],?\s*$/

// Divergence volontaire, prévue par le CA : une planche peut légitimement montrer une destination
// **à venir**, à condition de la déclarer — `// PLANCHE-A-VENIR: <id> — <pourquoi>`.
const A_VENIR = /^\s*\/\/\s*PLANCHE-A-VENIR:\s*([a-z-]+)\b/

interface Navigation {
  parDestination: Map<string, Axe>
  aVenir: Set<string>
}

function lireNavigation(source: string): Navigation {
  const parDestination = new Map<string, Axe>()
  const aVenir = new Set<string>()
  const connus = new Set<string>(AXES.map((a) => a.axe))
  let courant: Axe | null = null
  for (const ligne of source.split('\n')) {
    // `?.[1]` et non `[1]` : sous `noUncheckedIndexedAccess`, un groupe de capture est
    // `string | undefined` même quand le motif garantit sa présence.
    const aVenirIci = A_VENIR.exec(ligne)?.[1]
    if (aVenirIci) {
      aVenir.add(aVenirIci)
      continue
    }
    // ⚠️ La fermeture remet l'axe à zéro : sans elle, un couple écrit **après** le bloc
    // `DESTINATIONS` serait rattaché au dernier axe ouvert et compté comme une destination.
    if (FERMETURE.test(ligne)) {
      courant = null
      continue
    }
    const axe = SECTION.exec(ligne)?.[1]
    if (axe) {
      courant = connus.has(axe) ? (axe as Axe) : null
      continue
    }
    const destination = COUPLE.exec(ligne)?.[1]
    if (destination && courant) parDestination.set(destination, courant)
  }
  return { parDestination, aVenir }
}

interface Ecarts {
  manquantes: string[]
  fantomes: string[]
  malRangees: string[]
}

/** Ce qui sépare la navigation des maquettes de celle du produit.
 *
 * ⚠️ Asymétrie **voulue** (CA d'E17US010) : une maquette en avance sur le produit se déclare et
 * passe ; une destination livrée qu'aucune maquette ne montre reste rouge sans échappatoire —
 * c'est le sens de dérive qui fait relire des planches périmées.
 */
function ecarts(source: string): Ecarts {
  const { parDestination, aVenir } = lireNavigation(source)
  const produit = Object.entries(AXE_PAR_DESTINATION) as [string, Axe][]
  const manquantes = produit.filter(([id]) => !parDestination.has(id)).map(([id]) => id)
  const fantomes = [...parDestination.keys()].filter(
    (id) => !(id in AXE_PAR_DESTINATION) && !aVenir.has(id),
  )
  const malRangees = produit
    .filter(([id, axe]) => parDestination.has(id) && parDestination.get(id) !== axe)
    .map(([id, axe]) => `${id} : produit « ${axe} », maquettes « ${parDestination.get(id)} »`)
  return { manquantes, fantomes, malRangees }
}

describe('la navigation des maquettes suit celle du produit', () => {
  const source = readFileSync(APPAREILS, 'utf8')

  it('reconnaît la forme du fichier de maquettes', () => {
    // Sans ce contrôle, un reformatage d'`appareils.js` ferait échouer les trois suivants en
    // annonçant 33 destinations disparues — un diagnostic qui envoie chercher au mauvais endroit.
    expect(lireNavigation(source).parDestination.size).toBeGreaterThan(0)
  })

  it('ne laisse aucune destination du produit absente des maquettes', () => {
    expect(ecarts(source).manquantes).toEqual([])
  })

  it('ne laisse aucune destination de maquette absente du produit', () => {
    expect(ecarts(source).fantomes).toEqual([])
  })

  it('range chaque destination dans le même axe des deux côtés', () => {
    expect(ecarts(source).malRangees).toEqual([])
  })
})

describe('le garde-fou lui-même', () => {
  // Éprouvé sur une source factice, et pas seulement sur le fichier réel : un garde-fou dont on ne
  // voit jamais le rouge est un garde-fou dont on ignore s'il en a un (leçon de `DETTE-085`).
  const factice = (lignes: string[]) => ['  var DESTINATIONS = {', ...lignes, '  }'].join('\n')
  const pilotage = (couples: string[]) => factice(['    pilotage: [', ...couples, '    ],'])

  it('signale une destination de maquette inconnue du produit', () => {
    expect(ecarts(pilotage(["      ['jamais-livre', 'Écran rêvé'],"])).fantomes).toEqual([
      'jamais-livre',
    ])
  })

  it('tolère la même destination si elle est déclarée à venir', () => {
    const source = pilotage([
      '      // PLANCHE-A-VENIR: jamais-livre — maquette prospective, aucune route produit',
      "      ['jamais-livre', 'Écran rêvé'],",
    ])
    expect(ecarts(source).fantomes).toEqual([])
  })

  it('signale une destination rangée dans le mauvais axe', () => {
    const source = pilotage(["      ['clubs', 'Clubs'],"])
    expect(ecarts(source).malRangees).toEqual([
      'clubs : produit « atelier », maquettes « pilotage »',
    ])
  })

  it('signale une destination du produit que les maquettes oublient', () => {
    expect(ecarts(pilotage([])).manquantes).toContain('accueil')
  })
})
