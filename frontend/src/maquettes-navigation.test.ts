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

const DEBUT_TABLE = /^\s*var DESTINATIONS = \{\s*$/
const FIN_TABLE = /^\s*\}\s*$/
const SECTION = /^\s*([a-z]+):\s*\[\s*$/
const FERMETURE = /^\s*\],?\s*$/
const COUPLE = /^\s*\[\s*['"]([a-z0-9-]+)['"],\s*['"][^'"]*['"]\s*\],?\s*$/
const COMMENTAIRE = /^\s*\/\//

// ⚠️ La table se lit par **liste blanche** : dans le littéral, une ligne qui n'est ni section, ni
// fermeture, ni couple, ni commentaire, ni vide est **signalée**. Un parseur qui jette ce qu'il ne
// sait pas lire échoue **ouvert** — mesuré deux fois en revue, chaque fois en escamotant un
// fantôme (un commentaire de fin de ligne, puis un bloc entier sous un axe inconnu).
const ECRITURE_HORS_TABLE =
  /\bDESTINATIONS\b\s*(?:\s*\[[^\]]*\]|\.\w+)*\s*(?:=[^=]|\.push|\.concat|\.splice|\.unshift)/

// Divergence volontaire, prévue par le CA : une planche peut montrer une destination **à venir**.
// ⚠️ Motif **strict** — identifiant, tiret cadratin, puis une raison d'au moins deux mots. Une
// échappatoire gratuite se pose sans y penser, et c'est le seul mécanisme capable de désarmer ce
// contrôle. `A_VENIR_BRUT` rattrape les formes ratées pour que le rouge nomme la bonne ligne.
const A_VENIR = /^\s*\/\/\s*PLANCHE-A-VENIR:\s*([a-z0-9-]+)\s+—\s+\S+(?:\s+\S+)+\s*$/
const A_VENIR_BRUT = /^\s*\/\/\s*PLANCHE-A-VENIR/

interface Navigation {
  parDestination: Map<string, Axe>
  aVenir: Set<string>
  doublons: string[]
  nonReconnues: string[]
  axesInconnus: string[]
  aVenirNonConsommees: string[]
}

function lireNavigation(source: string): Navigation {
  const parDestination = new Map<string, Axe>()
  const aVenir = new Set<string>()
  const doublons: string[] = []
  const nonReconnues: string[] = []
  const axesInconnus: string[] = []
  const aVenirNonConsommees: string[] = []
  let dansTable = false
  let courant: Axe | null = null
  // ⚠️ Une **annonce**, pas un ensemble : la déclaration ne vaut que pour la ligne qui la suit
  // immédiatement. Accumulée, elle dispensait un fantôme d'un autre axe cent lignes plus bas,
  // pendant que trois documents promettaient « sur la ligne qu'elle dispense ».
  let annonce: string | null = null

  for (const ligne of source.split('\n')) {
    if (!dansTable) {
      if (DEBUT_TABLE.test(ligne)) dansTable = true
      else if (ECRITURE_HORS_TABLE.test(ligne)) nonReconnues.push(ligne.trim())
      continue
    }
    if (FIN_TABLE.test(ligne)) {
      dansTable = false
      courant = null
      annonce = null
      continue
    }
    if (A_VENIR_BRUT.test(ligne)) {
      const declare = A_VENIR.exec(ligne)?.[1]
      if (annonce !== null) aVenirNonConsommees.push(annonce)
      if (declare !== undefined && courant) annonce = declare
      else {
        annonce = null
        nonReconnues.push(ligne.trim())
      }
      continue
    }
    // L'annonce se consomme **ici ou jamais** : toute autre ligne la périme, y compris un
    // commentaire ou une ligne vide. C'est ce qui fait tenir « sur la ligne qu'elle dispense ».
    const destination = COUPLE.exec(ligne)?.[1]
    if (destination !== undefined && courant && annonce === destination) aVenir.add(destination)
    else if (annonce !== null) aVenirNonConsommees.push(annonce)
    annonce = null
    if (COMMENTAIRE.test(ligne) || ligne.trim() === '') continue
    if (FERMETURE.test(ligne)) {
      courant = null
      continue
    }
    const axe = SECTION.exec(ligne)?.[1]
    if (axe !== undefined) {
      if (!AXES.some((a) => a.axe === axe)) axesInconnus.push(axe)
      courant = AXES.find((a) => a.axe === axe)?.axe ?? null
      continue
    }
    if (destination === undefined || !courant) {
      nonReconnues.push(ligne.trim())
      continue
    }
    // ⚠️ `Map.set` écrase : sans ce relevé, une destination listée sous deux axes ne compte qu'une
    // fois — celle du **dernier** bloc. Une entrée ajoutée sans que l'ancienne soit retirée passe
    // alors en vert dans un sens et rouge dans l'autre, au gré de l'ordre du fichier.
    if (parDestination.has(destination)) doublons.push(destination)
    parDestination.set(destination, courant)
  }
  if (annonce !== null) aVenirNonConsommees.push(annonce)
  return { parDestination, aVenir, doublons, nonReconnues, axesInconnus, aVenirNonConsommees }
}

interface Ecarts {
  manquantes: string[]
  fantomes: string[]
  malRangees: string[]
  doublons: string[]
  aVenirPerimees: string[]
  aVenirNonConsommees: string[]
  nonReconnues: string[]
  axesInconnus: string[]
}

/** Ce qui sépare la navigation des maquettes de celle du produit.
 *
 * ⚠️ Asymétrie **voulue** (CA d'E17US010) : une maquette en avance sur le produit se déclare et
 * passe ; une destination livrée qu'aucune maquette ne montre reste rouge **sans échappatoire** —
 * c'est ce sens de dérive qui fait relire des planches périmées.
 */
function ecarts(source: string): Ecarts {
  const lu = lireNavigation(source)
  const produit = Object.entries(AXE_PAR_DESTINATION)
  const manquantes = produit.filter(([id]) => !lu.parDestination.has(id)).map(([id]) => id)
  // `Object.hasOwn` et non `in` : `in` traverse la chaîne de prototypes, donc `constructor`
  // satisfaisait le motif d'identifiant **et** le test d'appartenance.
  const fantomes = [...lu.parDestination.keys()].filter(
    (id) => !Object.hasOwn(AXE_PAR_DESTINATION, id) && !lu.aVenir.has(id),
  )
  const malRangees = produit
    .filter(([id, axe]) => lu.parDestination.has(id) && lu.parDestination.get(id) !== axe)
    .map(([id, axe]) => `${id} : produit « ${axe} », maquettes « ${lu.parDestination.get(id)} »`)
  const aVenirPerimees = [...lu.aVenir].filter((id) => Object.hasOwn(AXE_PAR_DESTINATION, id))
  return { ...lu, manquantes, fantomes, malRangees, aVenirPerimees }
}

describe('la navigation des maquettes suit celle du produit', () => {
  const source = readFileSync(APPAREILS, 'utf8')

  it('reconnaît chaque ligne de la table de navigation', () => {
    // ⚠️ Mesure la **couverture** du parseur, pas sa non-nullité : un `size > 0` restait vert quand
    // un seul bloc cessait d'être lu, et faisait alors annoncer des destinations disparues qui
    // n'avaient pas bougé — le diagnostic trompeur que ce contrôle existe pour éviter.
    const lu = lireNavigation(source)
    expect(lu.nonReconnues).toEqual([])
    expect(lu.axesInconnus).toEqual([])
    expect(new Set(lu.parDestination.values())).toEqual(new Set(AXES.map((a) => a.axe)))
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

  it('ne garde aucune déclaration « à venir » périmée ni inutile', () => {
    expect(ecarts(source).aVenirPerimees).toEqual([])
    expect(ecarts(source).aVenirNonConsommees).toEqual([])
  })
})

describe('le garde-fou lui-même', () => {
  // Éprouvé sur une source factice, et pas seulement sur le fichier réel : un garde-fou dont on ne
  // voit jamais le rouge est un garde-fou dont on ignore s'il en a un (leçon de `DETTE-085`).
  const factice = (lignes: string[]) => ['  var DESTINATIONS = {', ...lignes, '  }'].join('\n')
  const bloc = (axe: string, couples: string[]) => [`    ${axe}: [`, ...couples, '    ],']
  const pilotage = (couples: string[]) => factice(bloc('pilotage', couples))
  const REVE = "      ['jamais-livre', 'Écran rêvé'],"
  const DECLARE = '      // PLANCHE-A-VENIR: jamais-livre — maquette prospective, aucune route'

  it('signale une destination de maquette inconnue du produit', () => {
    expect(ecarts(pilotage([REVE])).fantomes).toEqual(['jamais-livre'])
  })

  it('tolère la même destination si elle est déclarée à venir, avec sa raison', () => {
    expect(ecarts(pilotage([DECLARE, REVE])).fantomes).toEqual([])
  })

  it('refuse une déclaration « à venir » sans raison, et le dit', () => {
    const source = pilotage(['      // PLANCHE-A-VENIR: jamais-livre', REVE])
    expect(ecarts(source).fantomes).toEqual(['jamais-livre'])
    expect(ecarts(source).nonReconnues).toEqual(['// PLANCHE-A-VENIR: jamais-livre'])
  })

  it('refuse une déclaration « à venir » dont la raison tient en un mot', () => {
    const source = pilotage(['      // PLANCHE-A-VENIR: jamais-livre — plus-tard', REVE])
    expect(ecarts(source).fantomes).toEqual(['jamais-livre'])
  })

  it('refuse une déclaration « à venir » posée hors de la table', () => {
    const source = ['  // PLANCHE-A-VENIR: jamais-livre — posée avant la table', pilotage([REVE])]
    expect(ecarts(source.join('\n')).fantomes).toEqual(['jamais-livre'])
  })

  it('refuse une déclaration « à venir » qui ne précède pas immédiatement sa ligne', () => {
    // La borne « sur la ligne qu'elle dispense » est écrite dans ADR-0112 §4, dans `appareils.js`
    // et dans la story : accumulée, elle dispensait un fantôme d'un **autre axe**.
    const source = factice([...bloc('pilotage', [DECLARE]), ...bloc('atelier', [REVE])])
    expect(ecarts(source).fantomes).toEqual(['jamais-livre'])
  })

  it('signale une déclaration « à venir » que rien ne consomme', () => {
    const source = pilotage([DECLARE, "      ['accueil', 'Accueil (tableau de bord)'],"])
    expect(ecarts(source).aVenirNonConsommees).toEqual(['jamais-livre'])
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
    expect(ecarts(pilotage(["      ['clubs', 'Clubs'],"])).malRangees).toEqual([
      'clubs : produit « atelier », maquettes « pilotage »',
    ])
  })

  it('signale une destination listée deux fois', () => {
    const source = pilotage(["      ['clubs', 'Clubs'],", "      ['clubs', 'Clubs'],"])
    expect(ecarts(source).doublons).toEqual(['clubs'])
  })

  it('signale un bloc dont l’axe est inconnu du produit, sans avaler ses lignes', () => {
    // Trou introduit par le correctif de la 1ʳᵉ passe : `if (!courant) continue` sautait le filet,
    // donc un axe inventé emportait toutes ses destinations en silence. Prouvé par sabotage.
    const source = factice(bloc('reglages', [REVE]))
    expect(ecarts(source).axesInconnus).toEqual(['reglages'])
    expect(ecarts(source).nonReconnues).toEqual(["['jamais-livre', 'Écran rêvé'],"])
  })

  it('signale une ligne de couple que le motif strict ne sait pas lire', () => {
    // Le cas prouvé par sabotage en 1ʳᵉ passe : un commentaire de fin de ligne suffisait à
    // escamoter un fantôme, parce qu'une ligne non reconnue était **jetée**.
    const source = pilotage(["      ['doublons', 'Doublons'], // fantôme escamoté"])
    expect(ecarts(source).nonReconnues).toEqual(["['doublons', 'Doublons'], // fantôme escamoté"])
  })

  it('signale une ligne intruse dans la table', () => {
    const source = pilotage(["      ['accueil', 'Accueil (tableau de bord)'],"]).replace(
      '    ],',
      '    ].concat(HERITAGE),',
    )
    expect(ecarts(source).nonReconnues).toEqual(['].concat(HERITAGE),'])
  })

  it('signale une écriture de la table faite en dehors du littéral', () => {
    const source = `${pilotage([])}\n  DESTINATIONS.gestion.push(['doublons', 'Doublons'])`
    expect(ecarts(source).nonReconnues).toEqual([
      "DESTINATIONS.gestion.push(['doublons', 'Doublons'])",
    ])
  })

  it('signale une destination du produit que les maquettes oublient', () => {
    expect(ecarts(pilotage([])).manquantes).toContain('accueil')
  })
})
