// Garde-fou de la charte (E17US001, ADR-0074).
//
// Ces tests ne vérifient pas un composant : ils vérifient que **la palette reste à un seul
// endroit**. C'est le seul invariant qui empêche la dérive qui a produit cette US — 98 US livrées
// sur un socle provisoire, chacune conforme à *son* CA, aucune en position de voir le problème.
//
// Ils dérivent des CA de l'US, pas de l'implémentation : chaque `describe` cite la puce dont il
// vient. Les fichiers sont lus **en source** plutôt qu'via le DOM, parce qu'on veut attraper une
// couleur écrite dans une feuille de style qu'aucun test ne monte.

import { describe, expect, it } from 'vitest'

// Lecture **sur disque**, pas par `import.meta.glob(..., '?raw')` : Vite traite une feuille `.css`
// comme un module de style et en renvoie le contenu injecté — soit une chaîne vide sous test. On
// veut le texte source, donc on le lit comme du texte.
//
// Fins de ligne normalisées : le dépôt est développé sous Windows, et un `\r` traînant ferait
// échouer les recherches multi-lignes pour une raison sans rapport avec la charte.
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

// Depuis `process.cwd()` et non `import.meta.url` : sous Vitest, l'URL d'un module n'est pas de
// schéma `file:` (elle passe par le serveur de modules), et `fileURLToPath` la refuse. La racine
// d'exécution est `frontend/`, celle du `package.json` qui porte le script de test.
const RACINE = join(process.cwd(), 'src')

function sourcesDe(dossier: string): [string, string][] {
  return readdirSync(dossier, { withFileTypes: true }).flatMap((entree) => {
    const chemin = join(dossier, entree.name)
    if (entree.isDirectory()) return sourcesDe(chemin)
    if (!/\.(css|tsx)$/.test(entree.name)) return []
    const relatif = chemin.slice(RACINE.length + 1).replace(/\\/g, '/')
    return [[relatif, readFileSync(chemin, 'utf8').replace(/\r\n/g, '\n')] as [string, string]]
  })
}

const SOURCES = Object.fromEntries(sourcesDe(RACINE))

const CHEMIN_CHARTE = 'index.css'
const charte = SOURCES[CHEMIN_CHARTE] as string
const features = Object.entries(SOURCES).filter(([chemin]) => chemin !== CHEMIN_CHARTE)

/** Le dernier sélecteur ouvert avant chaque ligne — pour dire *où* une faute se trouve. */
function lignesAvecSelecteur(source: string): { selecteur: string; ligne: string }[] {
  let selecteur = '(hors règle)'
  return source.split('\n').map((ligne) => {
    if (/\{\s*$/.test(ligne)) selecteur = ligne.replace(/\s*\{\s*$/, '').trim()
    return { selecteur, ligne }
  })
}

describe('CA — aucune couleur écrite hors de la charte', () => {
  // Les seules exceptions admises ont une raison **physique**, commentée sur place : un QR sur fond
  // sombre ne se scanne pas. Le test les nomme une par une — une cinquième apparaîtrait en échec.
  const EXCEPTIONS_PHYSIQUES = ['.qr-cible__vignette', '.qr-cible__grand', '.qr-cible__aide']

  it('aucune valeur hexadécimale hors `index.css`, sauf les exceptions physiques nommées', () => {
    const fautes = features.flatMap(([chemin, source]) =>
      lignesAvecSelecteur(source)
        .filter(
          ({ ligne }) => /#[0-9a-f]{3,8}\b/i.test(ligne) && !ligne.trimStart().startsWith('*'),
        )
        .filter(({ selecteur }) => !EXCEPTIONS_PHYSIQUES.includes(selecteur))
        .map(({ selecteur, ligne }) => `${chemin} — ${selecteur} — ${ligne.trim()}`),
    )

    expect(fautes).toEqual([])
  })

  it('aucun jeton du walking skeleton ne survit', () => {
    // `--warn` et `--ok` ne sont pas seulement renommés : ils ont **fusionné** dans `--danger` et
    // `--success`. Les laisser vivre en alias aurait reconduit les deux vocabulaires.
    const abandonnes = ['--accent', '--warn', '--ok', '--dim', '--text-h', '--bg', '--surface']
    const fautes = features.flatMap(([chemin, source]) =>
      abandonnes
        .filter((jeton) => source.includes(`var(${jeton})`))
        .map((jeton) => `${chemin} utilise ${jeton}`),
    )

    expect(fautes).toEqual([])
  })
})

describe('CA — les jetons portent les valeurs de la charte mesurée', () => {
  it.each([
    ['--surface-0', '#1d1d1b', 'fond de la banderole du club (DV-02)'],
    ['--brand-surface', '#b71918', 'rouge club, aplat seulement (DV-04)'],
    ['--danger', '#ffb000', "l'alerte est ambre, jamais rouge (DV-03)"],
    ['--success', '#22d3aa', ''],
    ['--text', '#ffffff', '16,88:1 sur l’anthracite'],
  ])('%s vaut %s en thème sombre — %s', (jeton, valeur) => {
    expect(charte).toContain(`${jeton}: ${valeur};`)
  })

  it("l'ambre du thème sombre est remplacé en thème clair, où il tomberait à 1,83:1", () => {
    expect(charte).toContain('--danger: #9f6d00;')
  })
})

describe('CA — chaque déclinaison de thème redéfinit l’ensemble des jetons', () => {
  // Le bug que ce test attrape n'a pas de symptôme visible en développement : un jeton oublié dans
  // une déclinaison **hérite silencieusement** de la valeur de l'autre thème, et le contraste
  // s'effondre sur le seul poste qui a basculé — un jour de compétition, dans un gymnase.
  function jetonsDuBloc(selecteur: string): string[] {
    const depart = charte.indexOf(selecteur)
    expect(depart, `bloc introuvable : ${selecteur}`).toBeGreaterThan(-1)
    const bloc = charte.slice(depart, charte.indexOf('\n}', depart))
    return [...bloc.matchAll(/^\s*(--[a-z0-9-]+):/gm)].map((m) => m[1] as string).sort()
  }

  const sombre = jetonsDuBloc(":root[data-theme='dark'] {")

  it('le thème clair définit exactement les mêmes jetons que le sombre', () => {
    expect(jetonsDuBloc(":root[data-theme='light'] {")).toEqual(sombre)
  })

  it('la déclinaison claire de « Système » (D-26) définit les mêmes jetons', () => {
    expect(jetonsDuBloc(":root[data-theme='systeme'] {")).toEqual(sombre)
  })
})

describe('CA — le rouge du club est une surface, jamais un accent (DV-04)', () => {
  it("`--brand-surface` n'est jamais une encre, ni le contour d'autre chose que lui-même", () => {
    // 2,55:1 sur l'anthracite : en texte comme en contour, il échoue. Ce sont `--brand-text`
    // (4,52:1) et `--brand-border` (3,01:1) qui existent pour ça.
    //
    // Une exception, et une seule : le **bord d'un aplat de marque**. Quand la règle pose déjà
    // `background: var(--brand-surface)`, le contour ne sépare pas la marque du fond — il affleure
    // sa propre surface, et aucun contraste n'est en jeu. Lui imposer `--brand-border` tracerait un
    // liseré plus clair d'1 px que les planches n'ont pas. D'où un jugement **par règle** et non par
    // ligne : c'est la présence de l'aplat dans le même bloc qui rend le contour légitime.
    const fautes = features.flatMap(([chemin, source]) =>
      source.split('\n}').flatMap((bloc) => {
        const selecteur = [...bloc.matchAll(/^(.*)\{\s*$/gm)].at(-1)?.[1]?.trim() ?? '?'
        const estUnAplat = /(^|\n)\s*background(-color)?:\s*var\(--brand-surface\)/.test(bloc)
        return bloc
          .split('\n')
          .filter((ligne) => {
            const encre = /^\s*(color|fill|stroke)\s*:[^;]*var\(--brand-surface\)/.test(ligne)
            const contour = /^\s*border[a-z-]*\s*:[^;]*var\(--brand-surface\)/.test(ligne)
            return encre || (contour && !estUnAplat)
          })
          .map((ligne) => `${chemin} — ${selecteur} — ${ligne.trim()}`)
      }),
    )

    expect(fautes).toEqual([])
  })

  it('tout aplat de marque porte une encre explicite', () => {
    // Sinon la règle hérite de l'encre du bouton principal — blanc sur ambre, 1,9:1.
    const aplats = features.flatMap(([chemin, source]) =>
      source
        .split('\n}')
        .filter((bloc) =>
          /background(-color)?:\s*var\(--(brand-surface|danger|success)\)/.test(bloc),
        )
        .filter((bloc) => !/(^|\n)\s*color:/.test(bloc))
        // Le bloc commence après l'accolade précédente : il inclut donc le commentaire qui
        // introduit la règle. Le sélecteur est la **dernière** ligne ouvrante, pas la première.
        .map(
          (bloc) => `${chemin} — ${[...bloc.matchAll(/^(.*)\{\s*$/gm)].at(-1)?.[1]?.trim() ?? '?'}`,
        ),
    )

    // Les pastilles de la checklist sont des points de couleur **sans texte** : rien à encrer.
    expect(aplats.filter((a) => !a.includes('checklist__pastille'))).toEqual([])
  })
})
