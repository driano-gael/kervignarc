/// <reference types="node" />

// Garde-fou d'E17US010 — la navigation des maquettes suit celle du produit (ADR-0112).
//
// `maquettes/assets/appareils.js` transcrit l'ossature d'`axes.ts` **à la main** : chaque US qui
// ajoute, renomme ou déplace une destination la désynchronise en silence, et on relit alors des
// planches décrivant une application qui n'existe plus. Le produit est lu par **import**, jamais
// par regex — un seul des deux côtés est parsé, donc un seul peut mentir sur sa propre forme.

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { AXES, AXE_PAR_DESTINATION } from './features/admin/axes'
import type { Axe } from './features/admin/axes'

// `process.cwd()` est la racine du projet Vite (`frontend/`) et non ce répertoire : même parti que
// `commentaires.test.ts`, dont l'en-tête dit pourquoi `import.meta.url` ne convient pas ici.
const APPAREILS = join(process.cwd(), '..', 'maquettes', 'assets', 'appareils.js')

const SECTION = /^\s*([a-z]+):\s*\[\s*$/
const FERMETURE = /^\s*\],?\s*$/
const COUPLE = /^\s*\['([a-z-]+)',\s*'[^']*'\],?\s*$/

// ⚠️ Motif **lâche**, et c'est son office : toute ligne qui *ressemble* à un couple doit avoir été
// reconnue par `COUPLE`. Sans cette mesure le parseur échoue **ouvert** — une entrée qu'il ne sait
// pas lire disparaît au lieu de rougir, et un fantôme se cache derrière un commentaire de fin de
// ligne. Démontré par sabotage en revue : `doublons` revenait, la suite restait verte.
const COUPLE_BRUT = /^\s*\[/

// Divergence volontaire, prévue par le CA : une planche peut montrer une destination **à venir**.
// ⚠️ La justification est **exigée par le motif** — une échappatoire gratuite se pose sans y
// penser, et c'est le seul mécanisme capable de désarmer ce contrôle.
const A_VENIR = /^\s*\/\/\s*PLANCHE-A-VENIR:\s*([a-z-]+)\s+—\s+\S/

interface Navigation {
  parDestination: Map<string, Axe>
  aVenir: Set<string>
  doublons: string[]
  nonReconnues: string[]
}

function lireNavigation(source: string): Navigation {
  const parDestination = new Map<string, Axe>()
  const aVenir = new Set<string>()
  const doublons: string[] = []
  const nonReconnues: string[] = []
  const connus = new Set<string>(AXES.map((a) => a.axe))
  let courant: Axe | null = null
  for (const ligne of source.split('\n')) {
    // ⚠️ Déclaration reçue **dans un bloc d'axe ouvert seulement** : posée dans la bannière du
    // fichier, elle dispensait une entrée située trois cents lignes plus bas, que personne ne
    // relie à elle en la lisant.
    const aVenirIci = A_VENIR.exec(ligne)?.[1]
    if (aVenirIci) {
      if (courant) aVenir.add(aVenirIci)
      continue
    }
    // ⚠️ La fermeture remet l'axe à zéro : sans elle, un couple écrit **après** le bloc
    // `DESTINATIONS` serait rattaché au dernier axe ouvert et compté comme une destination.
    if (FERMETURE.test(ligne)) {
      courant = null
      continue
    }
    // `?.[1]` et non `[1]` : sous `noUncheckedIndexedAccess`, un groupe de capture est
    // `string | undefined` même quand le motif garantit sa présence.
    const axe = SECTION.exec(ligne)?.[1]
    if (axe) {
      courant = connus.has(axe) ? (axe as Axe) : null
      continue
    }
    if (!courant) continue
    const destination = COUPLE.exec(ligne)?.[1]
    if (destination === undefined) {
      if (COUPLE_BRUT.test(ligne)) nonReconnues.push(ligne.trim())
      continue
    }
    // ⚠️ `Map.set` écrase : sans ce relevé, une destination listée sous deux axes ne compte qu'une
    // fois — celle du **dernier** bloc. Une entrée ajoutée sans que l'ancienne soit retirée passe
    // alors en vert dans un sens et rouge dans l'autre, au gré de l'ordre du fichier.
    if (parDestination.has(destination)) doublons.push(destination)
    parDestination.set(destination, courant)
  }
  return { parDestination, aVenir, doublons, nonReconnues }
}

interface Ecarts {
  manquantes: string[]
  fantomes: string[]
  malRangees: string[]
  doublons: string[]
  aVenirPerimees: string[]
  nonReconnues: string[]
}

/** Ce qui sépare la navigation des maquettes de celle du produit.
 *
 * ⚠️ Asymétrie **voulue** (CA d'E17US010) : une maquette en avance sur le produit se déclare et
 * passe ; une destination livrée qu'aucune maquette ne montre reste rouge **sans échappatoire** —
 * c'est ce sens de dérive qui fait relire des planches périmées.
 */
function ecarts(source: string): Ecarts {
  const { parDestination, aVenir, doublons, nonReconnues } = lireNavigation(source)
  const produit = Object.entries(AXE_PAR_DESTINATION)
  const manquantes = produit.filter(([id]) => !parDestination.has(id)).map(([id]) => id)
  // `Object.hasOwn` et non `in` : `in` traverse la chaîne de prototypes, donc `constructor`
  // satisfaisait le motif d'identifiant **et** le test d'appartenance.
  const fantomes = [...parDestination.keys()].filter(
    (id) => !Object.hasOwn(AXE_PAR_DESTINATION, id) && !aVenir.has(id),
  )
  const malRangees = produit
    .filter(([id, axe]) => parDestination.has(id) && parDestination.get(id) !== axe)
    .map(([id, axe]) => `${id} : produit « ${axe} », maquettes « ${parDestination.get(id)} »`)
  const aVenirPerimees = [...aVenir].filter((id) => Object.hasOwn(AXE_PAR_DESTINATION, id))
  return { manquantes, fantomes, malRangees, doublons, aVenirPerimees, nonReconnues }
}

describe('la navigation des maquettes suit celle du produit', () => {
  const source = readFileSync(APPAREILS, 'utf8')

  it('reconnaît chaque ligne du fichier de maquettes', () => {
    // ⚠️ Mesure la **couverture** du parseur, pas sa non-nullité : un `size > 0` restait vert quand
    // un seul bloc cessait d'être lu, et faisait alors annoncer des destinations disparues qui
    // n'avaient pas bougé — le diagnostic trompeur que ce contrôle existe pour éviter.
    const { parDestination, nonReconnues } = lireNavigation(source)
    expect(nonReconnues).toEqual([])
    expect(new Set(parDestination.values())).toEqual(new Set(AXES.map((a) => a.axe)))
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

  it('ne liste aucune destination deux fois', () => {
    expect(ecarts(source).doublons).toEqual([])
  })

  it('ne garde aucune déclaration « à venir » que sa livraison a périmée', () => {
    expect(ecarts(source).aVenirPerimees).toEqual([])
  })
})

describe('le garde-fou lui-même', () => {
  // Éprouvé sur une source factice, et pas seulement sur le fichier réel : un garde-fou dont on ne
  // voit jamais le rouge est un garde-fou dont on ignore s'il en a un (leçon de `DETTE-085`).
  const factice = (lignes: string[]) => ['  var DESTINATIONS = {', ...lignes, '  }'].join('\n')
  const pilotage = (couples: string[]) => factice(['    pilotage: [', ...couples, '    ],'])
  const REVE = "      ['jamais-livre', 'Écran rêvé'],"

  it('signale une destination de maquette inconnue du produit', () => {
    expect(ecarts(pilotage([REVE])).fantomes).toEqual(['jamais-livre'])
  })

  it('tolère la même destination si elle est déclarée à venir, avec sa raison', () => {
    const source = pilotage([
      '      // PLANCHE-A-VENIR: jamais-livre — maquette prospective, aucune route produit',
      REVE,
    ])
    expect(ecarts(source).fantomes).toEqual([])
  })

  it('refuse une déclaration « à venir » sans raison', () => {
    const source = pilotage(['      // PLANCHE-A-VENIR: jamais-livre', REVE])
    expect(ecarts(source).fantomes).toEqual(['jamais-livre'])
  })

  it("refuse une déclaration « à venir » posée hors d'un bloc d'axe", () => {
    const source = factice([
      "    // PLANCHE-A-VENIR: jamais-livre — posée loin de la ligne qu'elle dispense",
      '    pilotage: [',
      REVE,
      '    ],',
    ])
    expect(ecarts(source).fantomes).toEqual(['jamais-livre'])
  })

  it('ne laisse pas une déclaration « à venir » masquer une destination manquante', () => {
    // L'asymétrie est un CA : sans ce test, ajouter `&& !aVenir.has(id)` au filtre des manquantes
    // rendrait le garde-fou entièrement neutralisable par un commentaire, suite verte.
    const source = pilotage(['      // PLANCHE-A-VENIR: accueil — tentative de masquage'])
    expect(ecarts(source).manquantes).toContain('accueil')
  })

  it('signale une déclaration « à venir » que sa livraison a périmée', () => {
    const source = pilotage([
      '      // PLANCHE-A-VENIR: accueil — déclaration qui a survécu à sa livraison',
      "      ['accueil', 'Accueil (tableau de bord)'],",
    ])
    expect(ecarts(source).aVenirPerimees).toEqual(['accueil'])
  })

  it('signale une destination rangée dans le mauvais axe', () => {
    const source = pilotage(["      ['clubs', 'Clubs'],"])
    expect(ecarts(source).malRangees).toEqual([
      'clubs : produit « atelier », maquettes « pilotage »',
    ])
  })

  it('signale une destination listée deux fois', () => {
    const source = pilotage(["      ['clubs', 'Clubs'],", "      ['clubs', 'Clubs'],"])
    expect(ecarts(source).doublons).toEqual(['clubs'])
  })

  it('signale une ligne de couple que le motif strict ne sait pas lire', () => {
    // Le cas prouvé par sabotage en revue : un commentaire de fin de ligne suffisait à escamoter
    // un fantôme, parce qu'une ligne non reconnue était **jetée** au lieu d'être signalée.
    const source = pilotage(["      ['doublons', 'Doublons'], // fantôme escamoté"])
    expect(ecarts(source).nonReconnues).toEqual(["['doublons', 'Doublons'], // fantôme escamoté"])
  })

  it('signale une destination du produit que les maquettes oublient', () => {
    expect(ecarts(pilotage([])).manquantes).toContain('accueil')
  })
})
