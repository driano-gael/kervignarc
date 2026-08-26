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
function regles(source: string): { selecteurs: string[]; corps: string }[] {
  return [...source.matchAll(/([^{}]*)\{([^{}]*)\}/g)].map((m) => {
    // Le préambule contient le commentaire d'introduction **et** les éventuels sélecteurs du groupe,
    // un par ligne terminée d'une virgule. On remonte tant que la ligne précédente en est un : sans
    // ça, `.autre,\n.jauge span { … }` profitait de la dérogation accordée au seul dernier.
    const lignes = (m[1] ?? '').split('\n')
    let i = lignes.length - 1
    const selecteurs = [(lignes[i] ?? '').trim()]
    while (i > 0 && (lignes[i - 1] ?? '').trim().endsWith(',')) {
      i--
      selecteurs.unshift((lignes[i] ?? '').trim().replace(/,$/, ''))
    }
    return { selecteurs: selecteurs.filter((s) => s !== ''), corps: m[2] ?? '' }
  })
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

/** Le **groupe** de sélecteurs ouvert avant chaque ligne — pour dire *où* une faute se trouve, et
 *  pour qu'une dérogation ne puisse pas excuser ses voisins.
 *
 *  Le groupe, et non le dernier sélecteur : `.autre,\n.qr-cible__vignette { … }` faisait profiter
 *  `.autre` de la dérogation accordée au QR. Remis à zéro sur une accolade fermante, sinon les
 *  lignes hors règle héritent du groupe précédent. */
function lignesAvecSelecteur(source: string): { selecteurs: string[]; ligne: string }[] {
  const HORS = ['(hors règle)']
  let groupe = HORS
  let enAttente: string[] = []
  return source.split('\n').map((ligne) => {
    const brut = ligne.trim()
    const ouvre = ligne.match(/^(.*?)\{/)
    if (ouvre) {
      groupe = [...enAttente, (ouvre[1] ?? '').trim()].filter((s) => s !== '')
      enAttente = []
    } else if (brut.endsWith(',')) {
      enAttente.push(brut.slice(0, -1).trim())
    } else if (brut === '') {
      enAttente = []
    }
    const resultat = { selecteurs: groupe.length > 0 ? groupe : HORS, ligne }
    if (/\}/.test(ligne)) {
      groupe = HORS
      enAttente = []
    }
    return resultat
  })
}

/** Retire le **nom** d'un jeton, en gardant sa valeur de repli.
 *
 *  `var(--danger, #ff0000)` doit rester examinable : le repli est précisément l'idiome qu'on écrit
 *  quand un jeton manque, et effacer le `var()` entier laissait passer n'importe quel littéral —
 *  vérifié par mutation. On efface donc `var(--danger` et pas plus. */
function sansNomsDeJetons(texte: string): string {
  return texte.replace(/var\(\s*--[\w-]+/g, '')
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

  // Les seules exceptions admises, **nommées une par une avec leur raison**. Comparaison par
  // **égalité** de sélecteur : un `includes` excusait aussi `.jauge span.plein` ou
  // `.qr-cible__vignette-large`, c'est-à-dire des règles jamais examinées.
  //
  // Le compte est tenu par une assertion et non par une phrase : « une septième apparaîtrait en
  // échec » était devenu faux dès qu'E16US006 en a ajouté deux, et dans **ce** fichier un compte
  // faux est ce qui invite la suivante à passer sans discussion (relevé en revue).
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
    // Raison **logique** : une vignette d'aperçu doit montrer le rendu du thème qu'elle
    // représente, pas celui du poste qui la regarde (E16US006, `DV-05` : « aperçu sur les surfaces
    // réelles »). Peindre avec `var(--surface-0)` ferait s'afficher l'aperçu « thème sombre » en
    // blanc sur un poste en clair, soit l'inverse de ce qu'un aperçu existe pour faire. Les deux
    // valeurs sont celles de la charte (`DV-02`), recopiées et non choisies.
    '.identite__apercu--sombre .identite__scene': 'vignette figée en thème sombre',
    '.identite__apercu--clair .identite__scene': 'vignette figée en thème clair',
  }

  it('la liste des dérogations n’a pas grandi sans qu’on le remarque', () => {
    // Le seul contenu de ce test est son **chiffre**. Ajouter une dérogation devient donc un geste
    // délibéré : il faut venir mettre ce nombre à jour, et donc lire les raisons déjà inscrites.
    expect(Object.keys(COULEURS_ADMISES)).toHaveLength(8)
  })

  it('aucune couleur littérale hors `index.css`, sauf les exceptions nommées', () => {
    const fautes = features.flatMap(([chemin, source]) =>
      lignesAvecSelecteur(neutraliserCommentaires(source))
        .filter(({ ligne }) => COULEUR.test(sansNomsDeJetons(ligne)))
        // **Tous** les sélecteurs du groupe doivent être dérogés, pas seulement le dernier.
        .filter(({ selecteurs }) => !selecteurs.every((s) => Object.hasOwn(COULEURS_ADMISES, s)))
        .map(({ selecteurs, ligne }) => `${chemin} — ${selecteurs.join(', ')} — ${ligne.trim()}`),
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
    // `var\(\s*--brand-surface\s*[,)]` et non `var\(--brand-surface\)` : la forme **à repli**
    // `var(--brand-surface, #b71918)` échappait aux trois gardes de ce fichier.
    const MARQUE = String.raw`var\(\s*--brand-surface\s*[,)]`
    const fautes = features.flatMap(([chemin, source]) =>
      regles(source).flatMap(({ selecteurs, corps }) => {
        const estUnAplat = new RegExp(
          String.raw`(^|[;\n])\s*background(-color)?:\s*${MARQUE}`,
        ).test(corps)
        return corps
          .split(/[;\n]/)
          .filter((decl) => {
            const encre = new RegExp(String.raw`^\s*(color|fill|stroke)\s*:.*${MARQUE}`).test(decl)
            const contour = new RegExp(String.raw`^\s*border[a-z-]*\s*:.*${MARQUE}`).test(decl)
            return encre || (contour && !estUnAplat)
          })
          .map((decl) => `${chemin} — ${selecteurs.join(', ')} — ${decl.trim()}`)
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

    // L'encre doit être le jeton **apparié** au fond, pas une encre quelconque : `background:
    // var(--danger); color: var(--text)` est blanc sur ambre — 1,9:1 — et passait le contrôle de
    // simple présence. C'est exactement le défaut que ce test dit empêcher.
    const fautes = features.flatMap(([chemin, source]) =>
      regles(source)
        .filter(({ corps }) =>
          /(^|[;\n])\s*background(-color)?:\s*var\(--(brand-surface|danger|danger-strong|success|info)\)/.test(
            corps,
          ),
        )
        .filter(({ corps }) => !/(^|[;\n])\s*color:\s*var\(--sur-[\w-]+\)/.test(corps))
        .filter(({ selecteurs }) => !selecteurs.every((s) => REMPLISSAGES_SANS_TEXTE.includes(s)))
        .map(({ selecteurs }) => `${chemin} — ${selecteurs.join(', ')}`),
    )

    expect(fautes).toEqual([])
  })

  it('aucune feuille de feature ne redéfinit un jeton de la charte', () => {
    // Dernier chemin de contournement trouvé par mutation : `:root[data-theme='dark'] { --danger:
    // var(--brand-surface); }` posé dans une feuille de feature repeint toute l'alerte en rouge sans
    // écrire une seule couleur littérale, ni ressusciter un jeton abandonné. La palette « à un seul
    // endroit » exige donc aussi que **personne d'autre ne la redéfinisse**.
    const jetonsDeLaCharte = Object.keys(declinaison("data-theme='dark'").jetons)
    const fautes = features.flatMap(([chemin, source]) =>
      regles(neutraliserCommentaires(source)).flatMap(({ selecteurs, corps }) =>
        [...corps.matchAll(/(^|[;\n])\s*(--[a-z0-9-]+)\s*:/g)]
          .map((m) => m[2] as string)
          .filter((jeton) => jetonsDeLaCharte.includes(jeton))
          .map((jeton) => `${chemin} — ${selecteurs.join(', ')} — redéfinit ${jeton}`),
      ),
    )

    expect(fautes).toEqual([])
  })
})

// ————————————————————————————————————————————————————————————————————————————————————————————————

describe('CA — l’habillage de tournoi ne touche que le public et la salle (D-27, E16US006)', () => {
  // ⚠️ **Ce bloc transforme une intention en décision.** `HabillageIdentite.tsx` dit de lui-même que
  // `D-27` « n'est pas tenu par une condition mais par le **montage** » — ce qui est le bon choix de
  // conception, mais laissait la règle sans aucun gardien : rien n'empêchait une US future
  // d'importer l'habillage dans `CoquilleAdmin` ou dans un écran de saisie, et **aucun test
  // n'aurait bougé**. ADR-0097 §5 était donc appliqué sans être gardé — le mode de panne exact
  // d'ADR-0017 (treize mois), qu'ADR-0075 existe pour ne pas rejouer (relevé en revue).
  //
  // Il vit dans ce fichier et non dans `features/identite/` parce que la machinerie de lecture des
  // sources y est déjà, et parce que c'est bien la même question : **qui a le droit de toucher à la
  // marque**. Les deux blocs de ce fichier y répondent, l'un pour les jetons, l'autre pour la portée.

  const HABILLEURS = ['features/salle/EcranSalle.tsx', 'features/public/AccueilPublic.tsx']

  // Un seul module a le droit de fabriquer le CSS de marque : l'habillage lui-même, qui EST ce
  // mécanisme. Les deux habilleurs, eux, passent par lui et n'importent pas `jetons` directement.
  const PORTEURS_DE_JETONS = ['features/identite/HabillageIdentite.tsx']

  it('seuls l’écran de salle et l’appli publique importent l’habillage', () => {
    // ⚠️ **Le motif ne s'arrête pas à `from '…'`.** La rédaction précédente exigeait un import
    // statique, en quotes simples, se terminant exactement par le nom du module : un
    // `lazy(() => import('../identite/HabillageIdentite'))` — la façon normale de monter un écran
    // dans une coquille d'admin qu'on veut découper — passait au vert, tout comme des guillemets
    // doubles ou une extension explicite. Chercher le nom **suivi de sa quote fermante** couvre les
    // cinq formes, statiques et dynamiques.
    // ⚠️ **On cherche le NOM, pas le chemin.** Le contrôle demandait « qui importe ce module »,
    // ce qu'un porteur autorisé peut contourner en le **ré-exportant** : deux lignes
    // (`export { HabillageIdentite } from '…'` dans l'écran de salle, puis un import depuis l'admin)
    // habillaient l'admin avec les 29 tests au vert — mutation faite en revue. Un `.js` en fin de
    // spécificateur ou un alias de chemin suffisaient aussi. L'identifiant nu, lui, apparaît quelle
    // que soit la route empruntée ; le module qui le définit entre donc dans la liste attendue.
    const porteurs = features
      .filter(([, source]) => /\bHabillageIdentite\b/.test(neutraliserCommentaires(source)))
      .map(([chemin]) => chemin)
      .sort()

    expect(porteurs, 'D-27 : l’identité du tournoi n’habille jamais l’admin ni la saisie').toEqual(
      ['features/identite/HabillageIdentite.tsx', ...HABILLEURS].sort(),
    )
  })

  it('aucune feature ne court-circuite l’habillage en posant les jetons elle-même', () => {
    // Le point d'étranglement était à un module de profondeur : `cssDesJetons` suffit à peindre un
    // conteneur, sans jamais toucher `HabillageIdentite`. Un écran d'admin qui l'importerait
    // habillerait l'admin avec le contrôle précédent au vert — le garde-fou répondait à « qui monte
    // l'habillage », pas à la question que ce bloc pose lui-même : **qui a le droit de toucher à la
    // marque**.
    // `[^'"]*` et non `[.\w/]*` : un alias de chemin (`@/features/identite/jetons`) franchissait
    // le second. Aucun alias n'est configuré aujourd'hui — durcissement, pas trou vivant.
    const porteurs = features
      .filter(([, source]) =>
        /['"][^'"]*\/jetons(\.tsx?)?['"]/.test(neutraliserCommentaires(source)),
      )
      .map(([chemin]) => chemin)
      .sort()

    expect(porteurs, 'D-27 : les jetons de marque ne se posent qu’en salle et en public').toEqual(
      [...PORTEURS_DE_JETONS].sort(),
    )
  })

  it('les deux habilleurs existent encore sous ces noms', () => {
    // Garde-fou du garde-fou : renommés, les deux fichiers rendraient l'assertion précédente vraie
    // par un `[]` vide égal à un `[]` attendu — le mode de panne que ce fichier documente déjà.
    for (const chemin of HABILLEURS) {
      expect(SOURCES[chemin], `${chemin} introuvable`).toBeDefined()
    }
  })
})

describe('CA — la strate « marque » est la SEULE personnalisable par tournoi (DV-06, E16US006)', () => {
  // ⚠️ **Ce bloc ferme un trou que cette US a révélé.** Le contrôle « aucune feuille de feature ne
  // redéfinit un jeton de la charte » est écrit pour du CSS : il découpe la source en règles
  // `sélecteur { corps }`. Appliqué à un `.tsx` qui **fabrique** du CSS en chaîne de gabarit, il ne
  // voit rien — les `${…}` cassent son découpage. `jetons.ts` en fabriquait donc huit sans
  // qu'aucun test ne s'en aperçoive.
  //
  // La réponse n'est pas d'élargir la dérogation, c'est d'encoder la règle qui manquait. `DV-06`
  // décrit **trois strates** : marque *personnalisable*, sémantique et structure *figées*. Le
  // garde-fou ne connaissait que « la palette est à un seul endroit », ce qui est vrai de deux
  // strates sur trois. On vérifie donc ici la vraie règle, sur le seul module autorisé à l'exercer.

  const CHEMIN_JETONS = 'features/identite/jetons.ts'
  const fabrique = SOURCES[CHEMIN_JETONS] ?? ''

  /**
   * Une source pose-t-elle ce jeton ? Trois formes, parce qu'il y a trois façons d'écrire une
   * variable CSS depuis React : `{--x:${c}}` (deux-points collé), `{'--x': c}` (une quote
   * s'intercale) et `setProperty('--x', c)` (pas de deux-points du tout).
   *
   * ⚠️ **Écrit d'un seul endroit, et c'est le correctif.** Le motif avait été élargi pour surveiller
   * les *autres* features, mais le contrôle qui porte sur `jetons.ts` — le module dont ce bloc dit
   * qu'il est le seul autorisé à toucher la marque — gardait l'ancienne version étroite. Le trou
   * n'avait pas été fermé, il avait été déplacé sur le fichier le plus exposé (relevé en revue).
   */
  const poseLeJeton = (jeton: string, source: string) =>
    new RegExp(
      String.raw`(^|[^\w-])${jeton}\s*['"\`]?\s*:` +
        '|' +
        String.raw`setProperty\(\s*['"\`]${jeton}\b`,
    ).test(neutraliserCommentaires(source))

  // Les huit jetons de marque — quatre par accent. Eux seuls appartiennent à la strate
  // personnalisable ; tout le reste de la charte est figé.
  const JETONS_DE_MARQUE = [
    '--brand-surface',
    '--brand-border',
    '--brand-text',
    '--sur-brand',
    '--brand-2-surface',
    '--brand-2-border',
    '--brand-2-text',
    '--sur-brand-2',
  ]

  it('le mécanisme d’identité existe et pose bien des jetons', () => {
    // Garde-fou du garde-fou : renommé ou supprimé, le fichier rendrait les assertions suivantes
    // vraies par vacuité — exactement le mode de panne que ce fichier documente déjà deux fois.
    expect(fabrique, `${CHEMIN_JETONS} introuvable`).not.toBe('')
    expect(JETONS_DE_MARQUE.filter((jeton) => fabrique.includes(jeton))).toHaveLength(
      JETONS_DE_MARQUE.length,
    )
  })

  it('il ne pose AUCUN jeton hors de la strate marque', () => {
    // La liste des jetons figés se dérive de la charte elle-même : un jeton ajouté demain à
    // `index.css` entre de lui-même sous surveillance, sans qu'on ait à y penser.
    const figes = Object.keys(declinaison("data-theme='dark'").jetons).filter(
      (jeton) => !JETONS_DE_MARQUE.includes(jeton),
    )
    const fautes = figes.filter((jeton) => poseLeJeton(jeton, fabrique))

    expect(
      fautes,
      'un tournoi ne redéfinit ni les neutres ni les sémantiques (DV-03, DV-06 verrous 1 et 2)',
    ).toEqual([])
  })

  it('aucune AUTRE feature ne fabrique de CSS posant un jeton de la charte', () => {
    // Le mécanisme est **un**, et il est nommé. Une seconde feature qui se mettrait à émettre des
    // jetons rouvrirait la palette à plusieurs endroits — ce que tout ce fichier existe pour
    // empêcher. Détecté sur le texte brut (et non par le découpage en règles CSS), précisément
    // parce que c'est ce découpage qui ne voit pas les chaînes de gabarit.
    //
    // ⚠️ **La borne de gauche a été élargie, et c'est tout l'intérêt de ce commentaire.** La
    // première rédaction exigeait une apostrophe, un guillemet ou un accent grave *immédiatement*
    // devant le nom du jeton — c'est-à-dire exactement la mise en forme de `jetons.ts`, qui écrit
    // une déclaration par chaîne. Une feature qui aurait écrit la **règle entière** dans un seul
    // gabarit, `${porte}{--surface-0:${c}}` — la forme la plus naturelle, et celle que
    // `cssDesJetons` emploie lui-même pour assembler ses règles — repeignait le fond du produit
    // avec la suite au vert. Vérifié par mutation en revue adversariale : 25 tests passés.
    //
    // La borne actuelle accepte n'importe quel caractère non identifiant devant le jeton (ou le
    // début de la source). Le faux positif est quasi impossible : hors fabrication de CSS, un `.ts`
    // n'a aucune raison d'écrire `--surface-0:`, les commentaires sont déjà blanchis, et un
    // `var(--surface-0)` n'est pas suivi d'un deux-points.
    const jetonsDeLaCharte = Object.keys(declinaison("data-theme='dark'").jetons)
    const fautes = features
      .filter(([chemin]) => chemin !== CHEMIN_JETONS && /\.tsx?$/.test(chemin))
      .flatMap(([chemin, source]) =>
        jetonsDeLaCharte
          .filter((jeton) => poseLeJeton(jeton, source))
          .map((jeton) => `${chemin} fabrique ${jeton}`),
      )

    expect(fautes).toEqual([])
  })
})
