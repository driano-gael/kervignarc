// Tests de l'identité visuelle du tournoi (E16US006, absorbe E01US016).
//
// Ce que ces tests couvrent, et pourquoi ils sont des tests de **rendu** : le CA d'E16US006 ne porte
// sur aucun calcul côté front — la dérivation vit dans le domaine Python, éprouvée contre la
// déclinaison que la charte avait calculée à la main (`backend/tests/test_domain_identite.py`). Ce
// que cette moitié de l'US décide, c'est **ce qui s'affiche et où** : les jetons posés sur les deux
// bonnes surfaces, les logos rendus, le chiffre de contraste montré sans rien bloquer.
//
// ⚠️ **`DETTE-085` a établi le prix de l'omission** : un composant qui reçoit une donnée et ne la
// rend jamais passe `tsc` sans un mot, et aucun test ne monte l'écran. C'est exactement le bloquant
// d'`E16US005`. D'où les deux tests qui montent réellement `EcranSalle` et les vues publiques plutôt
// que le seul `HabillageIdentite` isolé — un test de placement doit monter **l'écran**.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EmplacementLogo, Identite as IdentiteDTO } from './api'
import { apercuIdentite, deposerLogo, enregistrerAccents, getIdentite, retirerLogo } from './api'
import { cssDesJetons } from './jetons'

/** Un emplacement pourvu, dans la forme du DTO : l'empreinte est le numéro de version du contenu. */
const pourvu = (emplacement: EmplacementLogo, empreinte = 'v1') => ({ emplacement, empreinte })
import { Identite } from './Identite'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getIdentite: vi.fn(),
  apercuIdentite: vi.fn(),
  enregistrerAccents: vi.fn(),
  deposerLogo: vi.fn(),
  retirerLogo: vi.fn(),
}))

/** Le rouge du club, décliné comme le serveur le rend — valeurs de `index.css` (E17US001). */
const IDENTITE_HERITEE: IdentiteDTO = {
  reglee: false,
  primaire: {
    couleur: '#b71918',
    sombre: {
      surface: '#b71918',
      contour: '#cc1c1b',
      texte: '#e84d4d',
      encre: '#ffffff',
    },
    clair: { surface: '#b71918', contour: '#b71918', texte: '#b71918', encre: '#ffffff' },
    contraste_sur_sombre: 2.55,
    contraste_sur_clair: 6.63,
  },
  secondaire: {
    couleur: '#1d1d1b',
    sombre: {
      surface: '#1d1d1b',
      contour: '#686860',
      texte: '#85857c',
      encre: '#ffffff',
    },
    clair: { surface: '#1d1d1b', contour: '#1d1d1b', texte: '#1d1d1b', encre: '#ffffff' },
    contraste_sur_sombre: 1.0,
    contraste_sur_clair: 16.88,
  },
  logos: [],
  seuil_contour: 3.0,
  seuil_texte: 4.5,
  poids_logo_max_octets: 512 * 1024,
}

function harnais(noeud: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{noeud}</QueryClientProvider>)
}

beforeEach(() => {
  // ⚠️ **`reset`, pas `clear`, et les CINQ doublures.** La configuration vitest du dépôt ne pose ni
  // `clearMocks` ni `restoreMocks`. `clearAllMocks` n'efface que le journal des appels : ni les
  // implémentations, ni la file des `mockResolvedValueOnce` — le commentaire précédent promettait
  // donc « l'ordre des tests indifférent » sans le tenir, et deux doublures restaient sans valeur
  // par défaut. `resetAllMocks` remet tout à plat, et les cinq sont restubées ici.
  vi.resetAllMocks()
  vi.mocked(getIdentite).mockResolvedValue(IDENTITE_HERITEE)
  vi.mocked(apercuIdentite).mockResolvedValue(IDENTITE_HERITEE)
  vi.mocked(enregistrerAccents).mockResolvedValue({ ...IDENTITE_HERITEE, reglee: true })
  vi.mocked(deposerLogo).mockResolvedValue(IDENTITE_HERITEE)
  vi.mocked(retirerLogo).mockResolvedValue(IDENTITE_HERITEE)
})

// ————————————————————————————————————————————————————————————————————————————————————————————————
// CA — « le système dérive […] en thème sombre ET clair » · les trois strates de `DV-06`

describe('CA — les jetons posés sur une surface', () => {
  it('émet les trois déclinaisons de thème, comme la charte', () => {
    // En omettre une laisserait la surface hériter des jetons du **club** sur ce thème-là : un
    // tournoi à moitié habillé, sans la moindre erreur visible. C'est le mode de panne que
    // `charte.test.ts` décrit déjà pour `index.css` (« un jeton oublié dans un thème est un bug de
    // contraste silencieux ») ; il vaut mot pour mot ici.
    const css = cssDesJetons('identite-7', IDENTITE_HERITEE)

    expect(css).toContain("[data-identite='identite-7']{")
    expect(css).toContain(":root[data-theme='light'] [data-identite='identite-7']{")
    expect(css).toContain("@media(prefers-color-scheme:light){:root[data-theme='systeme']")
  })

  it('pose la variante DÉRIVÉE en texte, et la couleur exacte en aplat', () => {
    // Le cœur de `DV-05`, vu du front : l'aplat garde `#b71918` — la marque du club — pendant que
    // le texte reçoit `#e84d4d`, qui tient 4,5:1 sur l'anthracite. Inverser les deux rendrait un
    // écran de salle dont les libellés sont illisibles à dix mètres, sans erreur nulle part.
    const css = cssDesJetons('identite-7', IDENTITE_HERITEE)

    expect(css).toContain('--brand-surface:#b71918')
    expect(css).toContain('--brand-text:#e84d4d')
    expect(css).toContain('--brand-border:#cc1c1b')
  })

  it('scope les jetons à la surface habillée, jamais à `:root`', () => {
    // Un `:root` poserait l'identité d'un tournoi sur **toute** l'application, y compris l'admin —
    // ce que `D-27` interdit. Le sélecteur est donc un attribut, et il porte l'identifiant du
    // tournoi : deux tournois ouverts côte à côte ne peuvent pas se repeindre l'un l'autre.
    const css = cssDesJetons('identite-7', IDENTITE_HERITEE)

    expect(css).not.toMatch(/(^|})\s*:root\s*{/)
    expect(cssDesJetons('identite-9', IDENTITE_HERITEE)).toContain("[data-identite='identite-9']")
  })

  it('n’émet AUCUN jeton sémantique ni structurel', () => {
    // `DV-06`, verrous 1 et 2 : « un tournoi ne redéfinit pas ce que "hors ligne" veut dire », et
    // « les neutres ne bougent pas ». Repeindre `--surface-0` invaliderait d'un coup les vingt
    // ratios que la charte a mesurés contre lui. Doublé par `charte.test.ts`, qui le vérifie sur
    // la source ; ici on le vérifie sur la **sortie**.
    const css = cssDesJetons('identite-7', IDENTITE_HERITEE)

    for (const fige of ['--surface-0', '--text', '--border', '--danger', '--success', '--info']) {
      expect(css, `${fige} ne doit pas être personnalisable`).not.toContain(`${fige}:`)
    }
  })
})

// ————————————————————————————————————————————————————————————————————————————————————————————————
// CA — « défaut = identité du club si rien n'est fourni »

describe('CA — hériter et avoir choisi ne se lisent pas pareil', () => {
  it('annonce l’héritage quand rien n’a été réglé', () => {
    harnais(<Identite tournoiId={7} />)

    return waitFor(() =>
      expect(screen.getByText(/hérite de l’identité du club/i)).toBeInTheDocument(),
    )
  })

  it('cesse de l’annoncer une fois les couleurs choisies', async () => {
    // ⚠️ Assertion **négative appariée** à la positive ci-dessus : sans cette paire, le test
    // resterait vert si le message disparaissait des deux écrans (libellé renommé, composant qui
    // ne rend plus rien).
    vi.mocked(getIdentite).mockResolvedValue({ ...IDENTITE_HERITEE, reglee: true })
    harnais(<Identite tournoiId={7} />)

    await waitFor(() => expect(screen.getByText(/Couleur principale/i)).toBeInTheDocument())
    expect(screen.queryByText(/hérite de l’identité du club/i)).toBeNull()
  })
})

// ————————————————————————————————————————————————————————————————————————————————————————————————
// CA — « contrôle de contraste à la saisie, en alerte CHIFFRÉE et NON BLOQUANTE » (P-4)

describe('CA — le contrôle de contraste', () => {
  it('affiche le ratio en chiffres, sur les deux thèmes', async () => {
    harnais(<Identite tournoiId={7} />)

    await waitFor(() => expect(screen.getAllByText(/2\.55:1/)).not.toHaveLength(0))
    expect(screen.getAllByText(/6\.63:1/)).not.toHaveLength(0)
  })

  it('dit qu’une couleur trop faible reste utilisée en aplat', async () => {
    // La moitié qui manque à la plupart des alertes de contraste : `P-4` veut qu'elle soit **non
    // bloquante**, donc l'écran doit dire que le produit y a déjà pourvu. Sans cette phrase,
    // l'organisateur lirait un avertissement et changerait sa marque pour rien.
    harnais(<Identite tournoiId={7} />)

    // Deux des quatre mesures échouent — les deux accents du club sur fond **sombre** (2,55:1 et
    // 1:1) — et deux passent, sur fond clair (6,63:1 et 16,88:1). Compter les deux côtés plutôt que
    // de chercher une occurrence : un écran qui dirait « trop faible » partout, ou nulle part,
    // passerait un `getAllByText` sans être vu.
    await waitFor(() => expect(screen.getAllByText(/votre couleur reste l’aplat/i)).toHaveLength(2))
    expect(screen.getAllByText(/lisible partout/i)).toHaveLength(2)
  })

  it('ne désactive JAMAIS l’enregistrement à cause du contraste', async () => {
    // Le rouge du club échoue à 2,55:1 sur l'anthracite — le cas d'école de `DV-04`. Un bouton
    // grisé ici retirerait sa marque à un club dont la charte est faible, ce que `DV-05` interdit
    // en toutes lettres.
    harnais(<Identite tournoiId={7} />)

    const bouton = await screen.findByRole('button', { name: /Enregistrer les couleurs/i })
    expect(bouton).toBeEnabled()
  })

  it('enregistre les deux accents saisis', async () => {
    harnais(<Identite tournoiId={7} />)

    const champ = await screen.findByLabelText(/Couleur principale — code hexadécimal/i)
    await userEvent.clear(champ)
    await userEvent.type(champ, '#0b6e9e')
    await userEvent.click(screen.getByRole('button', { name: /Enregistrer les couleurs/i }))

    await waitFor(() =>
      expect(vi.mocked(enregistrerAccents)).toHaveBeenCalledWith(7, {
        primaire: '#0b6e9e',
        secondaire: '#1d1d1b',
      }),
    )
  })
})

// ————————————————————————————————————————————————————————————————————————————————————————————————
// CA — « un second logo, FACULTATIF, distinct du logo d'événement » (E16US006, questionnaire A05)

describe('CA — les deux logos', () => {
  it('offre DEUX dépôts distincts', async () => {
    harnais(<Identite tournoiId={7} />)

    expect(
      await screen.findByLabelText(/Logo du tournoi — choisir un fichier/i),
    ).toBeInTheDocument()
    expect(
      screen.getByLabelText(/Logo du club organisateur — choisir un fichier/i),
    ).toBeInTheDocument()
  })

  it('distingue « pas assez pour du texte » de « pas même pour un contour »', async () => {
    // ⚠️ Le correctif visible le plus riche de la passe précédente n'était tenu par **aucun** test :
    // `seuil_contour` pouvait disparaître de bout en bout sans rougir, alors que
    // `docs/fonctionnel/E16US006.md` promet la phrase au recetteur, mot pour mot.
    //
    // La fixture héritée ne suffisait pas à le prouver : ses deux accents sont sous 3:1 sur fond
    // sombre, donc les deux porteraient l'incise et rien ne montrerait qu'elle est **absente**
    // quand elle doit l'être. On pose donc un secondaire à 4,0:1 — en échec du seul seuil de texte.
    vi.mocked(getIdentite).mockResolvedValue({
      ...IDENTITE_HERITEE,
      secondaire: { ...IDENTITE_HERITEE.secondaire, contraste_sur_sombre: 4.0 },
    })
    harnais(<Identite tournoiId={7} />)

    expect(await screen.findAllByText(/ni même pour un contour \(3:1\)/)).toHaveLength(1)
    expect(screen.getAllByText(/trop faible pour du texte \(4\.5:1 attendu\)/)).toHaveLength(2)
  })

  it('dit « aucun logo » plutôt que d’afficher un cadre vide', async () => {
    harnais(<Identite tournoiId={7} />)

    await waitFor(() => expect(screen.getAllByText(/Aucun logo/i)).toHaveLength(2))
  })

  it('n’offre le retrait que sur un emplacement pourvu', async () => {
    vi.mocked(getIdentite).mockResolvedValue({ ...IDENTITE_HERITEE, logos: [pourvu('club')] })
    harnais(<Identite tournoiId={7} />)

    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: /Retirer ce logo/i })).toHaveLength(1),
    )
    // Apparié : l'emplacement resté vide dit toujours son absence.
    expect(screen.getAllByText(/Aucun logo/i)).toHaveLength(1)
  })

  it('dépose le fichier sur l’emplacement de son libellé', async () => {
    // ⚠️ **Le geste central de l'écran n'était exercé par aucun test.** `deposerLogo` était mocké
    // et personne ne vérifiait qu'il soit appelé, ni avec quel emplacement : échanger
    // `emplacement="evenement"` et `emplacement="club"` entre les deux `<DepotDeLogo>` laissait
    // **toute la suite verte** en envoyant chaque fichier au mauvais endroit — c'est-à-dire le CA
    // « déposer l'un ne remplace pas l'autre » cassé, sans un test rouge (relevé en revue).
    //
    // `emplacement` et `libelle` sont deux props indépendantes : c'est leur **appariement** que ce
    // test tient, en partant du libellé que l'organisateur lit à l'écran.
    vi.mocked(deposerLogo).mockResolvedValue({ ...IDENTITE_HERITEE, logos: [pourvu('club')] })
    harnais(<Identite tournoiId={7} />)
    const fichier = new File(['x'], 'club.png', { type: 'image/png' })

    await userEvent.upload(
      await screen.findByLabelText(/Logo du club organisateur — choisir un fichier/i),
      fichier,
    )

    await waitFor(() => expect(vi.mocked(deposerLogo)).toHaveBeenCalledWith(7, 'club', fichier))
  })

  it('n’envoie pas au serveur un fichier que la limite affichée exclut', async () => {
    // Pré-contrôle de **confort** : le serveur reste juge et refuse la même chose. Sans lui, un
    // fichier de plusieurs mégaoctets traverse le Wi-Fi du gymnase pour revenir en 422, alors que
    // l'écran annonce la limite deux lignes plus haut.
    harnais(<Identite tournoiId={7} />)
    const tropLourd = new File([new Uint8Array(600 * 1024)], 'gros.png', { type: 'image/png' })

    await userEvent.upload(
      await screen.findByLabelText(/Logo du tournoi — choisir un fichier/i),
      tropLourd,
    )

    expect(await screen.findByText(/la limite est de 512 Ko/i)).toBeInTheDocument()
    expect(vi.mocked(deposerLogo)).not.toHaveBeenCalled()
  })

  it('montre le fichier remplacé, sans rechargement de page', async () => {
    // ⚠️ **Le geste que la passe précédente avait cassé en croyant l'améliorer.**
    //
    // L'URL d'un logo était versionnée par l'horodatage React Query — qui change à chaque événement
    // WebSocket, donc retéléchargeait 512 Ko pour rien. Le correctif a retiré le paramètre… et une
    // URL **stable** ne provoque plus aucune requête sur une image déjà montée : React ne réécrit
    // pas un attribut inchangé, le navigateur ne consulte même pas son cache, et
    // `Cache-Control: no-cache` ne s'applique à rien. Remplacer un logo ne changeait plus rien à
    // l'écran (mesuré en revue, `setAttribute` instrumenté).
    //
    // Le test suit le **geste réel** — déposer un fichier par-dessus un logo existant — plutôt que
    // de forcer un re-rendu : c'est la chaîne entière qui doit tenir (mutation → invalidation →
    // relecture → nouvelle empreinte → nouvel attribut `src`).
    vi.mocked(getIdentite)
      .mockResolvedValueOnce({ ...IDENTITE_HERITEE, logos: [pourvu('club', 'avant')] })
      .mockResolvedValue({ ...IDENTITE_HERITEE, logos: [pourvu('club', 'apres')] })
    vi.mocked(deposerLogo).mockResolvedValue({
      ...IDENTITE_HERITEE,
      logos: [pourvu('club', 'apres')],
    })
    harnais(<Identite tournoiId={7} />)
    const avant = await screen.findByRole('img', { name: /Logo du club organisateur déposé/i })
    expect(avant.getAttribute('src')).toContain('v=avant')

    await userEvent.upload(
      screen.getByLabelText(/Logo du club organisateur — choisir un fichier/i),
      new File(['neuf'], 'club.png', { type: 'image/png' }),
    )

    await waitFor(() =>
      expect(
        screen.getByRole('img', { name: /Logo du club organisateur déposé/i }).getAttribute('src'),
        'un contenu neuf donne une URL neuve — sinon l’image affichée ne bouge jamais',
      ).toContain('v=apres'),
    )
  })

  it('retire le logo de l’emplacement pourvu', async () => {
    vi.mocked(getIdentite).mockResolvedValue({ ...IDENTITE_HERITEE, logos: [pourvu('club')] })
    vi.mocked(retirerLogo).mockResolvedValue(IDENTITE_HERITEE)
    harnais(<Identite tournoiId={7} />)

    await userEvent.click(await screen.findByRole('button', { name: /Retirer ce logo/i }))

    await waitFor(() => expect(vi.mocked(retirerLogo)).toHaveBeenCalledWith(7, 'club'))
  })

  it('annonce le format et le poids acceptés', async () => {
    // Le fichier est fourni **déjà calibré** (arbitrage Q-UX10) : l'appli ne recadre rien et refuse
    // le reste. Le dire avant le dépôt évite un aller-retour dont la seule information serait un
    // message d'erreur.
    harnais(<Identite tournoiId={7} />)

    expect(await screen.findByText(/SVG ou PNG, 512 Ko au maximum/i)).toBeInTheDocument()
    expect(screen.getByText(/ni recadré ni détouré/i)).toBeInTheDocument()
  })
})

// ————————————————————————————————————————————————————————————————————————————————————————————————
// CA — « s'applique au public et à l'écran de salle UNIQUEMENT — jamais à l'admin » (D-27)

describe('CA — la portée de l’identité', () => {
  it('l’écran de préparation ne s’habille pas lui-même', async () => {
    // L'admin reste l'outil : « le jour J, un bénévole n'a pas le temps de réapprendre des repères
    // visuels ». L'organisateur voit le rendu dans des **vignettes**, pas en repeignant la page
    // sous ses pieds — et la vignette prouve que ce n'est pas un oubli d'affichage.
    const { container } = harnais(<Identite tournoiId={7} />)

    await waitFor(() => expect(screen.getByText(/Écran de salle/i)).toBeInTheDocument())
    expect(container.querySelector('[data-identite]')).toBeNull()
  })

  it('montre les DEUX thèmes en aperçu, pas un nuancier', async () => {
    // `DV-05` : « aperçu sur les surfaces réelles ». Un seul aperçu laisserait invisible la moitié
    // des cas — un accent peut tenir sur un thème et pas sur l'autre, c'est exactement la
    // situation du rouge du club.
    harnais(<Identite tournoiId={7} />)

    expect(await screen.findByText(/Écran de salle \(thème sombre\)/i)).toBeInTheDocument()
    expect(screen.getByText(/Téléphone du public \(thème clair\)/i)).toBeInTheDocument()
  })
})
