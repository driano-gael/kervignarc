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
const SECTION = /^\s*(['"])([a-z0-9-]+)\1?:\s*\[\s*$/
const FERMETURE = /^\s*\],?\s*$/
const CHAINE = /'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"/.source
const COUPLE = new RegExp(`^\\s*\\[\\s*(['"])([a-z0-9-]+)\\1,\\s*(?:${CHAINE})\\s*\\],?\\s*$`)
const SECTION_NUE = /^\s*([a-z0-9-]+):\s*\[\s*$/
const LIGNE = /^\s*\/\//

// ⚠️ **Liste blanche des deux côtés, sur la LIGNE ENTIÈRE.** Une lecture tolérée qui ne couvre
// qu'un fragment amnistiait tout le reste de la ligne : `DESTINATIONS.pilotage.pop(); …forEach(` a
// été mesuré vert. L'identifiant de boucle est libre — le figer faisait rougir un renommage pur,
// et c'est la **forme** de la lecture qui porte l'invariant, pas le nom de la variable.
const MENTION_TABLE = /\bDESTINATIONS\b/
const LECTURES_TOLEREES = [
  /^\s*DESTINATIONS\[[A-Za-z_$][\w$]*\]\.forEach\(function \(\w+\) \{$/,
  /^\s*var \w+ = DESTINATIONS\[[A-Za-z_$][\w$]*\] \|\| \[\]$/,
]

// Divergence volontaire, prévue par le CA : une planche peut montrer une destination **à venir**.
// ⚠️ Motif **strict** — identifiant, tiret cadratin, puis une raison d'au moins deux mots. Une
// échappatoire gratuite se pose sans y penser, et c'est le seul mécanisme capable de désarmer ce
// contrôle. `A_VENIR_BRUT` rattrape les formes ratées pour que le rouge nomme la bonne ligne.
const A_VENIR = /^\s*\/\/\s*PLANCHE-A-VENIR:\s*([a-z0-9-]+)\s+—\s+\S+(?:\s+\S+)+\s*$/
const A_VENIR_BRUT = /^\s*\/\/\s*PLANCHE-A-VENIR:\s*[a-z0-9-]/

interface Navigation {
  parDestination: Map<string, Axe>
  aVenir: Set<string>
  doublons: string[]
  nonReconnues: string[]
  axesInconnus: string[]
  axesDupliques: string[]
  aVenirNonConsommees: string[]
  lignesDeCode: string[]
}

/** Retire de la ligne ce qui est commenté, en suivant l'état de bloc d'une ligne à l'autre.
 *
 * ⚠️ **État lexical, pas motif de ligne.** Les quatre trous des passes 1 à 4 avaient la même
 * racine : un scan ligne à ligne sans mémoire. Un bloc `/* … *\/` posé dans la table faisait
 * compter ses entrées comme vivantes ; un `*\/` suivi de code faisait ignorer ce code.
 */
function decommenter(ligne: string, dansBloc: boolean): [string, boolean] {
  let reste = ligne
  let ouvert = dansBloc
  let sortie = ''
  for (;;) {
    if (ouvert) {
      const fin = reste.indexOf('*/')
      if (fin === -1) return [sortie, true]
      reste = reste.slice(fin + 2)
      ouvert = false
      continue
    }
    const debut = reste.indexOf('/*')
    if (debut === -1) return [sortie + reste, false]
    sortie += reste.slice(0, debut)
    reste = reste.slice(debut + 2)
    ouvert = true
  }
}

function lireNavigation(source: string): Navigation {
  const parDestination = new Map<string, Axe>()
  const aVenir = new Set<string>()
  const doublons: string[] = []
  const nonReconnues: string[] = []
  const axesInconnus: string[] = []
  const axesDupliques: string[] = []
  const aVenirNonConsommees: string[] = []
  const lignesDeCode: string[] = []
  const axesVus = new Set<string>()
  let dansBloc = false
  let dansTable = false
  let tableVue = false
  let courant: Axe | null = null
  // ⚠️ Une **annonce**, pas un ensemble : la déclaration ne vaut que pour la ligne qui la suit
  // immédiatement. Accumulée, elle dispensait un fantôme d'un autre axe cent lignes plus bas,
  // pendant que trois documents promettaient « sur la ligne qu'elle dispense ».
  let annonce: string | null = null

  for (const brute of source.split('\n')) {
    const commentaire = LIGNE.test(brute.trimStart()) ? brute : ''
    const [ligne, encore] = decommenter(brute, dansBloc)
    dansBloc = encore
    const nue = ligne.trim()
    if (nue !== '') lignesDeCode.push(ligne)

    if (!dansTable) {
      if (DEBUT_TABLE.test(ligne)) {
        // ⚠️ Un **second** littéral `var DESTINATIONS = {` n'est pas une continuation : en JS la
        // dernière affectation gagne, donc tout le premier disparaît du rendu.
        if (tableVue) nonReconnues.push(nue)
        tableVue = true
        dansTable = true
      } else if (A_VENIR_BRUT.test(commentaire)) nonReconnues.push(commentaire.trim())
      else if (LIGNE.test(nue) || nue === '') continue
      else if (MENTION_TABLE.test(ligne) && !LECTURES_TOLEREES.some((m) => m.test(ligne)))
        nonReconnues.push(nue)
      continue
    }
    if (FIN_TABLE.test(ligne)) {
      if (annonce !== null) aVenirNonConsommees.push(annonce)
      dansTable = false
      courant = null
      annonce = null
      continue
    }
    if (A_VENIR_BRUT.test(commentaire)) {
      const declare = A_VENIR.exec(commentaire)?.[1]
      if (annonce !== null) aVenirNonConsommees.push(annonce)
      if (declare !== undefined && courant) annonce = declare
      else {
        annonce = null
        nonReconnues.push(commentaire.trim())
      }
      continue
    }
    // L'annonce se consomme **ici ou jamais** : toute autre ligne la périme, y compris un
    // commentaire ou une ligne vide. C'est ce qui fait tenir « sur la ligne qu'elle dispense ».
    const destination = COUPLE.exec(ligne)?.[2]
    if (destination !== undefined && courant && annonce === destination) aVenir.add(destination)
    else if (annonce !== null) aVenirNonConsommees.push(annonce)
    annonce = null
    if (LIGNE.test(nue) || nue === '') continue
    if (FERMETURE.test(ligne)) {
      courant = null
      continue
    }
    const axe = SECTION.exec(ligne)?.[2] ?? SECTION_NUE.exec(ligne)?.[1]
    if (axe !== undefined) {
      // ⚠️ En JS, une clé répétée n'est pas une erreur : le **dernier** bloc écrase le premier.
      // Le parseur, lui, lisait leur union — donc neuf destinations pouvaient disparaître du rendu
      // sans que rien ne rougisse. Cause typique : un conflit de merge résolu par juxtaposition.
      if (!AXES.some((a) => a.axe === axe)) axesInconnus.push(axe)
      if (axesVus.has(axe)) axesDupliques.push(axe)
      axesVus.add(axe)
      courant = AXES.find((a) => a.axe === axe)?.axe ?? null
      continue
    }
    if (destination === undefined || !courant) {
      nonReconnues.push(nue)
      continue
    }
    // ⚠️ `Map.set` écrase : sans ce relevé, une destination listée sous deux axes ne compte qu'une
    // fois — celle du **dernier** bloc. Une entrée ajoutée sans que l'ancienne soit retirée passe
    // alors en vert dans un sens et rouge dans l'autre, au gré de l'ordre du fichier.
    if (parDestination.has(destination)) doublons.push(destination)
    parDestination.set(destination, courant)
  }
  if (annonce !== null) aVenirNonConsommees.push(annonce)
  if (dansBloc) nonReconnues.push('commentaire de bloc jamais refermé')
  return {
    parDestination,
    aVenir,
    doublons,
    nonReconnues,
    axesInconnus,
    axesDupliques,
    aVenirNonConsommees,
    lignesDeCode,
  }
}

interface Ecarts extends Navigation {
  manquantes: string[]
  fantomes: string[]
  malRangees: string[]
  aVenirPerimees: string[]
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
  // satisfait le motif d'identifiant **et** le test d'appartenance. Éprouvé plus bas.
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
    expect(lu.axesDupliques).toEqual([])
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

  it('fige les deux lignes de code qui lisent la table', () => {
    // ⚠️ **Couture, et rien de plus.** Elle voit qu'aucune ligne de code n'est ajoutée ni retirée
    // aux deux lectures connues. Elle ne voit **pas** ce qu'on fait de l'alias qu'une lecture rend
    // (`var liste = DESTINATIONS[axe] || []` puis `liste.splice(…)`) : cette borne est écrite en
    // ADR-0112 § Conséquences, parce qu'un garde-fou qui se croit plus large éteint la vigilance.
    const lectures = lireNavigation(source).lignesDeCode.filter((l) =>
      LECTURES_TOLEREES.some((m) => m.test(l)),
    )
    expect(lectures).toHaveLength(2)
  })
})

describe('le garde-fou lui-même', () => {
  // Éprouvé sur une source factice, et pas seulement sur le fichier réel : un garde-fou dont on ne
  // voit jamais le rouge est un garde-fou dont on ignore s'il en a un (leçon de `DETTE-085`).
  const factice = (lignes: string[]) => ['  var DESTINATIONS = {', ...lignes, '  }'].join('\n')
  const bloc = (axe: string, couples: string[]) => [`    ${axe}: [`, ...couples, '    ],']
  const pilotage = (couples: string[]) => factice(bloc('pilotage', couples))
  const REVE = "      ['jamais-livre', 'Écran rêvé'],"
  const ACCUEIL = "      ['accueil', 'Accueil (tableau de bord)'],"
  const DECLARE = '      // PLANCHE-A-VENIR: jamais-livre — maquette prospective, aucune route'

  it('signale une destination de maquette inconnue du produit', () => {
    expect(ecarts(pilotage([REVE])).fantomes).toEqual(['jamais-livre'])
  })

  it('signale une destination qui porte le nom d’une propriété héritée d’Object', () => {
    // `'constructor' in AXE_PAR_DESTINATION` vaut `true` : `in` la déclarerait livrée, et le
    // fantôme passerait. C'est le seul test qui épingle le choix de `Object.hasOwn`.
    expect(ecarts(pilotage(["      ['constructor', 'Piège']"])).fantomes).toEqual(['constructor'])
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

  it('laisse la documentation citer le gabarit sans le prendre pour une déclaration', () => {
    // Faux positif mesuré : l'en-tête d'`appareils.js` **documente** cette syntaxe. `<id>` n'est
    // pas un identifiant plausible, donc la citation ne doit rien déclarer ni rien signaler.
    const source = ['  // PLANCHE-A-VENIR: <id> — <pourquoi>', pilotage([ACCUEIL])].join('\n')
    expect(ecarts(source).nonReconnues).toEqual([])
  })

  it('refuse une déclaration « à venir » posée hors de la table, et la signale', () => {
    const declaration = '  // PLANCHE-A-VENIR: jamais-livre — posée avant la table'
    const source = [declaration, pilotage([REVE])].join('\n')
    expect(ecarts(source).fantomes).toEqual(['jamais-livre'])
    expect(ecarts(source).nonReconnues).toEqual([declaration.trim()])
  })

  it('refuse une déclaration « à venir » qui ne précède pas immédiatement sa ligne', () => {
    const source = factice([...bloc('pilotage', [DECLARE]), ...bloc('atelier', [REVE])])
    expect(ecarts(source).fantomes).toEqual(['jamais-livre'])
  })

  it('refuse une déclaration « à venir » séparée de sa ligne par une ligne vide', () => {
    expect(ecarts(pilotage([DECLARE, '', REVE])).fantomes).toEqual(['jamais-livre'])
  })

  it('signale une déclaration « à venir » que rien ne consomme', () => {
    expect(ecarts(pilotage([DECLARE, ACCUEIL])).aVenirNonConsommees).toEqual(['jamais-livre'])
  })

  it('ne laisse pas une déclaration « à venir » tenir lieu de destination', () => {
    // ⚠️ Depuis que l'annonce est locale, `aVenir ⊆ parDestination` : le masquage d'une manquante
    // est structurellement impossible. C'est la seconde assertion qui rougit si la péremption saute.
    const source = pilotage(['      // PLANCHE-A-VENIR: accueil — tentative de masquage'])
    expect(ecarts(source).manquantes).toContain('accueil')
    expect(ecarts(source).aVenirNonConsommees).toEqual(['accueil'])
  })

  it('signale une déclaration « à venir » que sa livraison a périmée', () => {
    const source = pilotage([
      '      // PLANCHE-A-VENIR: accueil — déclaration qui a survécu à sa livraison',
      ACCUEIL,
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

  it('signale une catégorie déclarée deux fois, que le navigateur écraserait', () => {
    const source = factice([...bloc('pilotage', [ACCUEIL]), ...bloc('pilotage', [REVE])])
    expect(ecarts(source).axesDupliques).toEqual(['pilotage'])
  })

  it('signale une seconde table, dont le navigateur ne garderait que la dernière', () => {
    const source = [pilotage([ACCUEIL]), factice(bloc('gestion', [REVE]))].join('\n')
    expect(ecarts(source).nonReconnues).toContain('var DESTINATIONS = {')
  })

  it('signale un bloc dont l’axe est inconnu du produit, sans avaler ses lignes', () => {
    const source = factice(bloc('reglages', [REVE]))
    expect(ecarts(source).axesInconnus).toEqual(['reglages'])
    expect(ecarts(source).nonReconnues).toEqual(["['jamais-livre', 'Écran rêvé'],"])
  })

  it('signale une ligne de couple que le motif strict ne sait pas lire', () => {
    const source = pilotage(["      ['doublons', 'Doublons'], // fantôme escamoté"])
    expect(ecarts(source).nonReconnues).toEqual(["['doublons', 'Doublons'], // fantôme escamoté"])
  })

  it('ne compte pas vivantes les entrées mises en commentaire de bloc dans la table', () => {
    // Trou de la 4ᵉ passe : le suivi de bloc ne valait qu'en dehors de la table, donc le geste le
    // plus banal — mettre un groupe de côté le temps d'une refonte — escamotait ses entrées.
    const source = pilotage(['      /* mis de côté', ACCUEIL, '      */'])
    expect(ecarts(source).manquantes).toContain('accueil')
  })

  it('examine le code écrit après la fin d’un commentaire de bloc', () => {
    // Régression de la 3ᵉ passe, trouvée par différentiel : `*/ <mutation>` était rouge, puis vert.
    const source = `${pilotage([ACCUEIL])}\n  /* note\n  */ DESTINATIONS.pilotage.pop()`
    expect(ecarts(source).nonReconnues).toEqual(['DESTINATIONS.pilotage.pop()'])
  })

  it('signale un commentaire de bloc que rien ne referme', () => {
    expect(ecarts(`${pilotage([ACCUEIL])}\n  /* jamais refermé`).nonReconnues).toEqual([
      'commentaire de bloc jamais refermé',
    ])
  })

  it('accepte un libellé qui porte une apostrophe droite entre guillemets doubles', () => {
    const source = pilotage(["      ['accueil', \"Accueil d'un tournoi\"],"])
    expect(ecarts(source).nonReconnues).toEqual([])
    expect(ecarts(source).manquantes).not.toContain('accueil')
  })

  it('refuse un identifiant dont les guillemets sont dépareillés', () => {
    // JS lirait `accueil"` ; le parseur lisait `accueil`, donc la planche cessait en silence de
    // marquer son lien actif.
    expect(ecarts(pilotage(["      ['accueil\", 'Accueil'],"])).manquantes).toContain('accueil')
  })

  it('signale une ligne intruse dans la table', () => {
    const source = pilotage([ACCUEIL]).replace('    ],', '    ].concat(HERITAGE),')
    expect(ecarts(source).nonReconnues).toEqual(['].concat(HERITAGE),'])
  })

  const horsLitteral = [
    "  DESTINATIONS.gestion.push(['doublons', 'Doublons'])",
    '  DESTINATIONS.pilotage.pop()',
    '  delete DESTINATIONS.atelier',
    "  Object.assign(DESTINATIONS, { reglages: [['x', 'X']] })",
    '  var alias = DESTINATIONS',
    '  DESTINATIONS.gestion.length = 0; DESTINATIONS[axe].forEach(function (d) {',
  ]
  it.each(horsLitteral)('signale « %s » hors du littéral', (mutation) => {
    // ⚠️ Liste **blanche** sur la ligne entière : `.push` était énuméré, `.pop` non ; et une lecture
    // tolérée présente sur la ligne amnistiait tout le reste. Les deux ont été mesurés verts.
    expect(ecarts(`${pilotage([])}\n${mutation}`).nonReconnues).toEqual([mutation.trim()])
  })

  it('laisse passer les deux lectures connues de la table', () => {
    const lectures = [
      '    DESTINATIONS[axe].forEach(function (d) {',
      '    var liste = DESTINATIONS[axe] || []',
    ]
    expect(ecarts(`${pilotage([])}\n${lectures.join('\n')}`).nonReconnues).toEqual([])
  })

  it('laisse passer les deux lectures après un renommage de la variable de boucle', () => {
    // Faux positif mesuré : figer le nom `axe` faisait rougir un renommage pur, avec un message
    // qui ne nommait ni le fichier ni le défaut. C'est la forme qui porte l'invariant.
    const lectures = [
      '    DESTINATIONS[axeOuvert].forEach(function (entree) {',
      '    var entrees = DESTINATIONS[axeOuvert] || []',
    ]
    expect(ecarts(`${pilotage([])}\n${lectures.join('\n')}`).nonReconnues).toEqual([])
  })

  it('signale une destination du produit que les maquettes oublient', () => {
    expect(ecarts(pilotage([])).manquantes).toContain('accueil')
  })
})
