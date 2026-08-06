// Garde-fou de la charte (E17US001, ADR-0074).
//
// Ces tests ne vérifient pas un composant : ils vérifient que **la palette reste à un seul
// endroit**. C'est le seul invariant qui empêche la dérive qui a produit cette US — 98 US livrées
// sur un socle provisoire, chacune conforme à *son* CA, aucune en position de voir le problème.
//
// Ils dérivent des CA de l'US, pas de l'implémentation : chaque `describe` cite la puce dont il
// vient. Les fichiers sont lus **en source** plutôt qu'via le DOM, parce qu'on veut attraper une
// couleur écrite dans une feuille de style qu'aucun test ne monte.
//
// ⚠️ **Durci à la revue d'E17US001** après qu'un relecteur adversarial eut fait passer **sept**
// diffs hostiles au vert. Les quatre causes, toutes corrigées ici, méritent d'être connues avant de
// retoucher ce fichier : (1) les valeurs étaient cherchées par `toContain` sur **tout** le fichier,
// donc un jeton juste dans *un* thème validait *tous* les thèmes ; (2) les blocs de thème étaient
// **codés en dur**, donc une quatrième déclinaison échappait à la comparaison ; (3) le découpage en
// règles se faisait sur `'\n}'`, qui ne coupe pas sur une accolade **indentée** — une `@media`
// entière comptait pour une seule règle ; (4) les dérogations étaient comparées par **sous-chaîne**.
// La leçon : ce fichier est le garde-fou, il ne se relâche pas pour laisser passer son auteur.

/// <reference types="node" />
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
// d'exécution est `frontend/`, celle du `package.json` qui porte le script de test — `ci.yml` fixe
// `working-directory: frontend`. Lancé d'ailleurs, `readdirSync` lève `ENOENT` au chargement du
// module : la panne est **bruyante**, jamais un faux vert.
const RACINE = join(process.cwd(), 'src')

function sourcesDe(dossier: string): [string, string][] {
  return readdirSync(dossier, { withFileTypes: true }).flatMap((entree) => {
    const chemin = join(dossier, entree.name)
    if (entree.isDirectory()) return sourcesDe(chemin)
    // Les `.ts` comptent aussi (une couleur peut vivre dans une constante), **sauf les tests** :
    // ce fichier-ci porte les valeurs de la charte en clair et se dénoncerait lui-même.
    if (!/\.(css|tsx?)$/.test(entree.name) || /\.test\.tsx?$/.test(entree.name)) return []
    const relatif = chemin.slice(RACINE.length + 1).replace(/\\/g, '/')
    return [[relatif, readFileSync(chemin, 'utf8').replace(/\r\n/g, '\n')] as [string, string]]
  })
}

const SOURCES = Object.fromEntries(sourcesDe(RACINE))

const CHEMIN_CHARTE = 'index.css'
const charteLue = SOURCES[CHEMIN_CHARTE]
const features = Object.entries(SOURCES).filter(([chemin]) => chemin !== CHEMIN_CHARTE)

// Pas de `as string` ici : sous `noUncheckedIndexedAccess`, l'accès est bien `string | undefined`, et
// le masquer ferait surgir la panne dix lignes plus bas sous forme de `TypeError` illisible. Le repli
// sur `''` est **sûr** parce qu'il est bruyant : la charte vide fait tomber le test ci-dessous *et*
// le décompte des déclinaisons, jamais un faux vert.
const charte = charteLue ?? ''

// Une panne de résolution doit se lire du premier coup d'œil.
it('les sources du front sont lisibles depuis le répertoire d’exécution', () => {
  expect(
    charteLue,
    'index.css introuvable — vitest doit être lancé depuis `frontend/`',
  ).toBeDefined()
  expect(features.length).toBeGreaterThan(5)
})

/** Énumère les règles d'une feuille : un couple *(sélecteur, corps)* par paire d'accolades.
 *
 *  **Ne pas revenir à un découpage sur les retours à la ligne.** Les deux tentatives précédentes ont
 *  chacune ouvert un trou vérifié : `'\n}'` ne coupe pas sur une accolade **indentée**, donc une
 *  `@media` entière comptait pour une seule règle — un aplat y légitimait le contour de toutes les
 *  autres ; et `/\n\s*\}/` rate les règles écrites **sur une seule ligne** (`.x { color: … }`), par
 *  lesquelles n'importe quelle violation de marque passait.
 *
 *  `[^{}]*` borne chaque corps à une règle sans accolade : la prélude d'une `@media` ne matche donc
 *  pas, et ce sont ses règles **internes** qui sont énumérées — exactement ce qu'on veut examiner. */
function regles(source: string): { selecteur: string; corps: string }[] {
  return [...source.matchAll(/([^{}]*)\{([^{}]*)\}/g)].map((m) => ({
    // Le préambule capturé contient le commentaire d'introduction ; le sélecteur en est la dernière
    // ligne.
    selecteur: ((m[1] ?? '').split('\n').at(-1) ?? '').trim(),
    corps: m[2] ?? '',
  }))
}

/** Blanchit le contenu des commentaires **en gardant les retours à la ligne**, pour que les numéros
 *  de ligne et le suivi des sélecteurs restent justes.
 *
 *  Indispensable au détecteur de couleurs : en JavaScript, une limite de mot ne traite pas les
 *  lettres accentuées comme des caractères de mot — chercher le nom de couleur `red` **matche donc
 *  « redémarrage »**. Sans ce nettoyage, la prose française du projet, abondante et voulue, noierait
 *  le test sous les faux positifs ; et la réaction naturelle aurait été d'affaiblir la détection,
 *  c'est-à-dire exactement le mode de panne que ce fichier existe pour empêcher. */
function neutraliserCommentaires(source: string): string {
  const blanchir = (texte: string) =>
    texte
      .split('\n')
      .map((ligne) => ' '.repeat(ligne.length))
      .join('\n')
  return source
    .replace(/\/\*[\s\S]*?\*\//g, blanchir)
    .replace(/(^|[^:])\/\/.*/g, (tout, avant: string) => avant + blanchir(tout.slice(avant.length)))
}

/** Le dernier sélecteur ouvert avant chaque ligne — pour dire *où* une faute se trouve. Remis à
 *  zéro sur une accolade fermante, sinon les lignes hors règle héritent du sélecteur précédent et
 *  se retrouvent couvertes par sa dérogation. */
function lignesAvecSelecteur(source: string): { selecteur: string; ligne: string }[] {
  let selecteur = '(hors règle)'
  return source.split('\n').map((ligne) => {
    const ouvre = ligne.match(/^(.*?)\{/)
    if (ouvre) selecteur = (ouvre[1] ?? '').trim()
    const resultat = { selecteur, ligne }
    if (/\}/.test(ligne)) selecteur = '(hors règle)'
    return resultat
  })
}

describe('CA — aucune couleur écrite hors de la charte', () => {
  // Toute notation, pas seulement l'hexadécimale : `rgb()`, `hsl()`, `oklch()` et les noms CSS
  // écrivent une couleur aussi sûrement que `#b71918`. Les `var(--…)` sont retirés avant l'examen,
  // sans quoi un `color-mix(in srgb, var(--brand-surface) 12%, transparent)` — parfaitement
  // légitime — serait dénoncé.
  //
  // Les noms sont bornés par `(?<![-\w])…(?![-\w])` et non par une simple limite de mot : sinon
  // `white-space: nowrap` est pris pour la couleur « white ». Un nom de couleur n'est une couleur
  // que s'il n'est pas un morceau de propriété.
  const COULEUR =
    /#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\s*\(|(?<![-\w])(?:white|black|red|green|blue|gr[ae]y|orange|yellow|purple|pink|brown|cyan|magenta|silver|gold|navy|teal|olive|maroon|lime|aqua|fuchsia)(?![-\w])/i

  // Les seules exceptions admises, **nommées une par une avec leur raison**. Une septième
  // apparaîtrait en échec. Comparaison par **égalité** de sélecteur : un `includes` excusait aussi
  // `.jauge span.plein` ou `.qr-cible__vignette-large`, c'est-à-dire des règles jamais examinées.
  const COULEURS_ADMISES: Record<string, string> = {
    // Raison **physique** : un QR sur fond sombre ne se scanne pas.
    '.qr-cible__vignette': 'fond blanc obligatoire pour la lecture du QR',
    '.qr-cible__grand': 'idem, en plein écran',
    '.qr-cible__aide': 'texte posé sur le voile noir de l’agrandissement',
    // Voiles et ombres : du **noir transparent**, pas une teinte. La charte ne les décrit pas parce
    // qu'ils ne sont pas de la couleur — ils sont de l'absence de lumière.
    '.qr-cible__overlay': 'voile d’agrandissement, noir transparent',
    '.dialogue': 'ombre portée, noir transparent',
    '.dialogue::backdrop': 'voile de modale, noir transparent',
  }

  it('aucune couleur littérale hors `index.css`, sauf les exceptions nommées', () => {
    const fautes = features.flatMap(([chemin, source]) =>
      lignesAvecSelecteur(neutraliserCommentaires(source))
        .filter(({ ligne }) => COULEUR.test(ligne.replace(/var\([^)]*\)/g, '')))
        .filter(({ selecteur }) => !(selecteur in COULEURS_ADMISES))
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

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Les déclinaisons de thème, **énumérées** et non codées en dur : une quatrième déclinaison ajoutée
// demain entre d'elle-même dans les comparaisons ci-dessous. C'est la correction du trou par lequel
// un thème entier échappait au contrôle.

interface Declinaison {
  selecteur: string
  jetons: Record<string, string>
}

const DECLINAISONS: Declinaison[] = [...charte.matchAll(/(:root[^{}]*?)\{([^{}]*)\}/g)]
  .map(([, selecteur, corps]) => ({
    selecteur: (selecteur ?? '').replace(/\s+/g, ' ').trim(),
    jetons: Object.fromEntries(
      [...(corps ?? '').matchAll(/^\s*(--[a-z0-9-]+):\s*([^;]+);/gm)].map((m) => [
        m[1] as string,
        (m[2] as string).trim().toLowerCase(),
      ]),
    ),
  }))
  // Une déclinaison de **couleur** se reconnaît à ce qu'elle pose la surface de fond. Le bloc
  // typographique (`--sans`, `--mono`) n'en est pas une et n'a pas à définir les mêmes jetons.
  .filter((d) => '--surface-0' in d.jetons)

function declinaison(fragment: string): Declinaison {
  const trouvee = DECLINAISONS.find((d) => d.selecteur.includes(fragment))
  expect(trouvee, `déclinaison introuvable : ${fragment}`).toBeDefined()
  return trouvee as Declinaison
}

describe('CA — les jetons portent les valeurs de la charte mesurée', () => {
  const sombre = declinaison("data-theme='dark'")
  const clair = declinaison("data-theme='light'")

  // Les valeurs sont vérifiées **dans leur bloc**. Avec l'ancien `toContain` sur le fichier entier,
  // il suffisait qu'une valeur existe *quelque part* — un thème pouvait donc porter l'ambre du
  // sombre (1,83:1 sur blanc, l'effondrement exact que le CA nomme) sans qu'aucun test ne bouge.
  it.each([
    ['--surface-0', '#1d1d1b', 'fond de la banderole du club (DV-02)'],
    ['--brand-surface', '#b71918', 'rouge club, aplat seulement (DV-04)'],
    ['--brand-text', '#e84e4d', 'la seule marque lisible en texte sur l’anthracite (4,52:1)'],
    ['--danger', '#ffb000', 'l’alerte est ambre, jamais rouge (DV-03)'],
    ['--danger-strong', '#ffd400', 'l’escalade de l’alerte, toujours ambre'],
    ['--success', '#22d3aa', 'transcrit de maquettes/assets/systeme.css'],
    ['--text', '#ffffff', '16,88:1 sur l’anthracite'],
    // La puce de CA la plus explicitement chiffrée : un contour actionnable (4,04:1) n'est pas un
    // séparateur décoratif (1,55:1) — WCAG 1.4.11.
    ['--border', '#7c7c7b', 'contour d’un élément actionnable, 4,04:1'],
    ['--border-subtle', '#3d3d3a', 'séparateur décoratif, 1,55:1'],
  ])('%s vaut %s en thème sombre — %s', (jeton, valeur) => {
    expect(sombre.jetons[jeton]).toBe(valeur)
  })

  it("l'ambre du sombre est remplacé en clair, où il tomberait à 1,83:1", () => {
    expect(clair.jetons['--danger']).toBe('#9f6d00')
    expect(clair.jetons['--danger']).not.toBe(sombre.jetons['--danger'])
  })

  it('en clair, le rouge de la charte redevient lisible en texte (6,63:1)', () => {
    expect(clair.jetons['--brand-text']).toBe('#b71918')
  })
})

describe('CA — chaque déclinaison de thème redéfinit l’ensemble des jetons', () => {
  // Le bug que ce test attrape n'a pas de symptôme visible en développement : un jeton oublié dans
  // une déclinaison **hérite silencieusement** de la valeur de l'autre thème, et le contraste
  // s'effondre sur le seul poste qui a basculé — un jour de compétition, dans un gymnase.
  const reference = declinaison("data-theme='dark'")

  it('il y a bien trois déclinaisons de couleur, et le test les a toutes vues', () => {
    // Garde-fou du garde-fou : si une déclinaison disparaît du fichier (ou si la regex cesse de la
    // reconnaître), les comparaisons ci-dessous deviendraient vraies par vacuité.
    expect(DECLINAISONS.map((d) => d.selecteur)).toHaveLength(3)
  })

  it.each(DECLINAISONS.map((d) => [d.selecteur]))(
    '%s définit exactement les mêmes jetons que la référence',
    (selecteur) => {
      const bloc = DECLINAISONS.find((d) => d.selecteur === selecteur) as Declinaison
      expect(Object.keys(bloc.jetons).sort()).toEqual(Object.keys(reference.jetons).sort())
    },
  )

  it('la déclinaison claire de « Système » (D-26) porte les valeurs du thème clair', () => {
    // Sans cette assertion, le bloc `systeme` pouvait être une copie du **sombre** : les noms
    // concordaient, donc le test précédent passait, et l'option « Système » ne faisait plus rien.
    expect(declinaison("data-theme='systeme'").jetons).toEqual(
      declinaison("data-theme='light'").jetons,
    )
  })
})

describe('CA — le rouge du club est une surface, jamais un accent (DV-04)', () => {
  it("`--brand-surface` n'est jamais une encre, ni le contour d'autre chose que lui-même", () => {
    // 2,55:1 sur l'anthracite : en texte comme en contour, il échoue. Ce sont `--brand-text`
    // (4,52:1) et `--brand-border` (3,01:1) qui existent pour ça.
    //
    // Une exception, et une seule : le **bord d'un aplat de marque**. Quand la règle pose déjà
    // `background: var(--brand-surface)`, le contour ne sépare pas la marque du fond — il affleure
    // sa propre surface, et aucun contraste n'est en jeu.
    const fautes = features.flatMap(([chemin, source]) =>
      regles(source).flatMap(({ selecteur, corps }) => {
        const estUnAplat = /(^|[;\n])\s*background(-color)?:\s*var\(--brand-surface\)/.test(corps)
        return corps
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

  it('tout aplat porteur de texte porte une encre explicite', () => {
    // Sinon la règle hérite de l'encre du bouton principal — blanc sur ambre, 1,9:1.
    //
    // L'invariant ne porte que sur les aplats **qui contiennent du texte** : une surface purement
    // décorative n'a rien à encrer. Le test ne sait pas lire le DOM depuis une feuille de style :
    // ces cas se déclarent un par un, **par égalité de sélecteur** — un `includes` excusait aussi
    // toute règle dont le sélecteur contenait le fragment.
    const REMPLISSAGES_SANS_TEXTE = [
      '.checklist__pastille--ok', // un point de couleur en regard d'une ligne
      '.checklist__pastille--alerte',
      '.jauge span', // le remplissage d'une jauge, dans sa piste
    ]

    const fautes = features.flatMap(([chemin, source]) =>
      regles(source)
        .filter(
          ({ corps }) =>
            /(^|[;\n])\s*background(-color)?:\s*var\(--(brand-surface|danger|danger-strong|success)\)/.test(
              corps,
            ) && !/(^|[;\n])\s*color:/.test(corps),
        )
        .filter(({ selecteur }) => !REMPLISSAGES_SANS_TEXTE.includes(selecteur))
        .map(({ selecteur }) => `${chemin} — ${selecteur}`),
    )

    expect(fautes).toEqual([])
  })
})
