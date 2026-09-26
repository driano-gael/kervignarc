// Test de **rendu** de l'écran de saisie du poste de cible — le premier de cet écran.
//
// CA d'E16US020 : « l'écran dit pourquoi le refus tombe — un refus muet serait pire que
// l'écrasement qu'il remplace ». ⚠️ **Monter l'écran, pas le message** : un test du seul
// `MessageErreurSaisie` resterait vert après l'avoir détaché du pavé — le défaut de `DETTE-085`,
// que `tsc` ne voit pas, une propriété calculée et jamais rendue ne cassant aucune compilation.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ErreurApi } from '../../shared/api/client'
import type { Serie, Volee } from './api'
import { Saisie } from './Saisie'
import { serieOptimiste } from './volees'

const LIGNE = {
  position: 'A',
  archer_id: 12,
  nom: 'DURAND',
  prenom: 'Léa',
  zones: ['10', '9', '8', 'M'],
  forfait: false,
}

function volee(numero: number, valeurs: string[], extra: Partial<Volee> = {}): Volee {
  return {
    numero,
    valeurs,
    saisie_par: 'DURAND',
    validee_par: null,
    verrouillee: false,
    en_correction: false,
    correction_ouverte_par: null,
    lot_validation: null,
    saisie_le: null,
    ...extra,
  }
}

// ⚠️ **Mutables, et remises à zéro à chaque cas.** Le défaut que cette US corrige vivait dans le
// **consommateur** (`LigneArcher` lisait `serie.cumul`), pas dans une fonction pure : le prouver
// demande de faire diverger `cumul` et `volees`, donc de poser la série cas par cas. ⚠️ **Typées** :
// sans le type, un champ renommé côté API laisserait ces tests verts sur une forme qui n'existe plus.
const SERIE_VIDE: Serie = { tournoi_id: 1, archer_id: 12, cumul: 0, volees: [] }
let SERIE: Serie = SERIE_VIDE
type EtatRequete = { data: unknown; isError: boolean; isSuccess: boolean; error: Error | null }
const GRILLE_SERVIE: EtatRequete = { data: [LIGNE], isError: false, isSuccess: true, error: null }
let GRILLE: EtatRequete = GRILLE_SERVIE

let erreurSaisie: Error | null = null

// La table que sert le barème (E17US011) : le poste la lit, il ne recalcule plus. Lue par la
// fabrique de `vi.mock` au rendu, donc après l'évaluation du module — `const` y est sûr.
const TABLE: Record<string, number> = { '10': 10, '9': 9, '8': 8, '7': 7, M: 0 }
const BAREME_SERVI = { data: { nb_volees: 2, nb_fleches_par_volee: 3, points_par_zone: TABLE } }
// Mutables, remis aux valeurs servies par `reinitialiserEtats` (revue d'E17US011 : barème illisible,
// série en cours de chargement — les deux cas où la ligne affichait un faux).
let BAREME: unknown = BAREME_SERVI
let SERIE_CHARGEE = true

vi.mock('./hooks', () => ({
  useRejeuFileHorsLigne: () => undefined,
  useGrille: () => GRILLE,
  useBareme: () => BAREME,
  useGrain: () => ({ data: null }),
  useDeparts: () => ({ data: [], isSuccess: true }),
  useFixerDepart: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  useSerie: () =>
    SERIE_CHARGEE
      ? { data: SERIE, isError: false, isSuccess: true, error: null }
      : { data: undefined, isError: false, isSuccess: false, error: null },
  useSeries: () => [{ data: SERIE, isSuccess: true }],
  useSaisirVolee: () => ({
    // ⚠️ `mutate` **joue** le rappel d'échec : un `vi.fn()` nu prouvait que la chaîne est rendue,
    // jamais qu'elle est vraie — c'est ce qui avait laissé passer le pavé qui affiche encore la
    // frappe refusée sous « le score affiché fait foi » (relevé en revue).
    mutate: (_corps: unknown, options?: { onError?: (e: Error) => void }) => {
      if (erreurSaisie) options?.onError?.(erreurSaisie)
    },
    isPending: false,
    isError: erreurSaisie !== null,
    error: erreurSaisie,
  }),
}))

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(<Saisie tournoiId={1} cibleIndex={1} />, { wrapper: Enveloppe })
}

// Le cumul de la première ligne d'archer, visé par sa classe : « 27 » et « 54 » apparaissent aussi
// dans la bande de relecture (totaux de volée), donc un `getByText` y serait ambigu.
async function cumulAffiche() {
  const grille = await screen.findByRole('list')
  return grille.querySelector('.saisie__cumul')?.textContent
}

async function ouvrirLePave() {
  monter()
  // ⚠️ Par la liste : « DURAND » figure AUSSI dans le sélecteur de marqueur, qui dérive de la
  // grille — un `findByText` y trouverait deux nœuds.
  const grille = await screen.findByRole('list')
  await userEvent.click(within(grille).getByRole('button', { name: /volées/ }))
}

describe('Saisie — un refus de préséance est expliqué', () => {
  // ⚠️ Sans cette remise à zéro, un cas qui oublierait d'affecter `erreurSaisie` hériterait
  // silencieusement de l'erreur du précédent et passerait pour la mauvaise raison : la suite
  // serait verte par ordre d'exécution, pas par construction.
  beforeEach(() => {
    erreurSaisie = null
    SERIE = SERIE_VIDE
    GRILLE = GRILLE_SERVIE
  })

  it('dit QUI a écrit et QUEL est le recours', async () => {
    erreurSaisie = new ErreurApi(
      409,
      'ecriture_de_role_inferieur',
      "Cette volée a été saisie par l'organisateur : seul un rôle au moins équivalent peut la modifier.",
    )

    await ouvrirLePave()

    const alerte = await screen.findByRole('alert')
    expect(alerte).toHaveTextContent(/saisie par l’organisateur|saisie par l'organisateur/)
    expect(alerte).toHaveTextContent(/signalez l’erreur à l’organisateur/)
  })

  it('efface la frappe refusée : le pavé retombe sur la vérité du serveur', async () => {
    erreurSaisie = new ErreurApi(409, 'ecriture_de_role_inferieur', 'Saisie par l’organisateur.')

    const { container } = monter()
    const grille = await screen.findByRole('list')
    await userEvent.click(within(grille).getByRole('button', { name: /volées/ }))
    for (let i = 0; i < 3; i += 1) {
      await userEvent.click(screen.getByRole('button', { name: '10' }))
    }
    expect(container.querySelector('.saisie__buffer')).toHaveTextContent('101010')

    await userEvent.click(screen.getByRole('button', { name: /Enregistrer la volée/ }))

    expect(container.querySelector('.saisie__buffer')).not.toHaveTextContent('10')
  })

  it('laisse les autres refus au message générique', async () => {
    // ⚠️ Sans ce jumeau, rendre le message de préséance pour TOUTE erreur passerait inaperçu :
    // le premier test resterait vert, et le marqueur lirait « signalez à l'organisateur » sur une
    // panne réseau ou un refus de cible.
    erreurSaisie = new ErreurApi(403, 'saisie_hors_cible', 'Archer hors de votre cible.')

    await ouvrirLePave()

    const alerte = await screen.findByRole('alert')
    expect(alerte).toHaveTextContent('Archer hors de votre cible.')
    expect(alerte).not.toHaveTextContent(/signalez/)
  })
})

describe('Saisie — le panneau du marqueur dit ce qu’on engage', () => {
  // CA d'E17US008, planche S04 : la liste nue de quatre noms ne disait pas à quoi sert ce choix, et
  // le verdict de la planche tranche — « sans elle, le geste paraît administratif ». Le test monte
  // l'écran et **ouvre** le panneau : la phrase vit dans une branche conditionnelle, un test du seul
  // libellé replié resterait vert si elle disparaissait.
  it('la phrase de justification est rendue avec la liste des archers', async () => {
    monter()

    const declencheur = await screen.findByRole('button', { name: /Marqueur/ })
    await userEvent.click(declencheur)

    expect(screen.getByText(/l’archer qui tient la tablette/)).toBeInTheDocument()
    expect(screen.getByText(/le scoreur vient contresigner/)).toBeInTheDocument()
    // La moitié qui vient de la variante « changer en cours de série » : ce qui est déjà saisi ne
    // change pas d'auteur. C'est elle qui lève la crainte de réécrire le passé.
    expect(screen.getByText(/gardent le nom de qui les a entrées/)).toBeInTheDocument()

    // La liste reste une liste, et elle porte bien l'archer de la grille.
    const choix = screen.getByRole('listbox', { name: 'Choisir le marqueur' })
    expect(within(choix).getByRole('button', { name: /DURAND/ })).toBeInTheDocument()
  })
})

describe('Saisie — le cumul affiché est celui qui est SAISI', () => {
  beforeEach(() => {
    erreurSaisie = null
    SERIE = SERIE_VIDE
    GRILLE = GRILLE_SERVIE
  })

  // ⚠️ **Le test doit vivre ICI, pas seulement dans `volees.test.ts`.** Le défaut n'était pas dans
  // `cumulSaisi` — qui n'existait pas — mais dans `LigneArcher`, qui lisait `serie.cumul`. Les
  // tests de la fonction pure resteraient **tous verts** si quelqu'un remettait `serie.cumul` au
  // rendu. C'est le motif de `DETTE-085`, que l'en-tête de ce fichier cite déjà.
  //
  // Oracle : questionnaire `s02-poste-de-cible.md`, question 3 — « en permanence, c'est un bon
  // rappel sur la cible ». Avec le grain « fin de série », le serveur rend 0 tout au long.
  it('affiche 54 là où le serveur rend un cumul de 0', async () => {
    SERIE = { ...SERIE_VIDE, volees: [volee(1, ['10', '9', '8']), volee(2, ['9', '9', '9'])] }
    monter()

    // ⚠️ Viser le **cumul**, pas un `getByText` : « 27 » figure aussi dans la bande de relecture,
    // comme total de volée. Un `getByText` ambigu ferait échouer le test pour la mauvaise raison.
    expect(await cumulAffiche()).toBe('54')
  })

  it('compte une volée partie hors ligne, que le serveur ignore encore', async () => {
    // La garantie d'E04US009, et la justification écrite de `DETTE-111` : le poste doit valoriser
    // ce que le serveur n'a **jamais reçu**. `serieOptimiste` ajoute la volée à `volees` sans
    // toucher `cumul` — si le rendu lisait `cumul`, le marqueur verrait 0 pendant la coupure.
    // ⚠️ Fixture construite par **`serieOptimiste` lui-même** — le code qui décide qu'une volée
    // partie dans la file entre dans `volees` sans toucher `cumul`. Écrite à la main, elle
    // n'aurait traversé aucun des deux.
    SERIE = serieOptimiste(SERIE_VIDE, {
      tournoi_id: 1,
      archer_id: 12,
      numero: 1,
      valeurs: ['10', '9', '8'],
      saisie_par: 'DURAND',
      identifiant_saisie: 'x1',
    })
    monter()

    expect(await cumulAffiche()).toBe('27')
  })

  it('compte une volée rendue en correction, alignement sur ADR-0109', async () => {
    // Côté serveur, une volée en correction **compte toujours** : son score tient. Le front doit
    // dire la même chose, sans quoi le total chuterait à l'instant du renvoi par le scoreur.
    SERIE = {
      ...SERIE_VIDE,
      volees: [volee(1, ['10', '9', '8'], { en_correction: true, validee_par: 'MOREAU' })],
    }
    monter()

    expect(await cumulAffiche()).toBe('27')
  })
})

describe('Saisie — le numéro de cible ne passe en géant que dans l’état « Rattaché »', () => {
  beforeEach(() => {
    erreurSaisie = null
    SERIE = SERIE_VIDE
    GRILLE = GRILLE_SERVIE
  })

  // Oracle : planche S01, état « Rattaché » — le numéro y est en 48 px, et la planche dit pourquoi :
  // « le seul moyen de repérer une tablette posée devant la mauvaise cible AVANT que quiconque
  // tire ». C'est une consigne de sécurité, donc la condition qui la déclenche mérite un test.
  const enGeant = () => document.querySelector('.saisie__entete--confirmation') !== null

  it('départ non fixé : le numéro est en géant', () => {
    GRILLE = {
      data: undefined,
      isError: true,
      isSuccess: false,
      error: new ErreurApi(409, 'depart_courant_non_defini', 'Départ courant non défini.'),
    }
    monter()

    expect(enGeant()).toBe(true)
  })

  it('grille en cours de chargement : PAS de géant', () => {
    // ⚠️ Le défaut que la condition resserrée ferme : `lignes.length === 0` seul était vrai pendant
    // le chargement, donc le numéro s'affichait en 48 px puis retombait à 22 px à chaque montage.
    GRILLE = { data: undefined, isError: false, isSuccess: false, error: null }
    monter()

    expect(enGeant()).toBe(false)
  })

  it('grille servie avec ses archers : PAS de géant', () => {
    monter()

    expect(enGeant()).toBe(false)
  })
})

// E17US011 — oracle : planche S02, la ligne est `pos | nom | fl fl fl | somme`, et la réserve écrite
// deux fois au questionnaire S02 : « l'appel du pavé doit se faire à la sélection de la zone de
// saisie ». Monté en entier : le geste traverse la ligne, `Saisie` (qui détient la visée) et le pavé.
describe('Saisie — la ligne d’archer porte la volée en cours', () => {
  beforeEach(() => {
    erreurSaisie = null
    SERIE = SERIE_VIDE
    GRILLE = GRILLE_SERVIE
  })

  async function caseDeLaLigne(numero: number) {
    const grille = await screen.findByRole('list')
    return within(grille).getByRole('button', { name: new RegExp(`^Flèche ${numero} de DURAND`) })
  }

  it('toucher une case ouvre le pavé, et la volée se remplit dans la ligne avec sa somme', async () => {
    monter()
    await userEvent.click(await caseDeLaLigne(1))
    for (const zone of ['10', '9', '8']) {
      await userEvent.click(screen.getByRole('button', { name: zone }))
    }

    expect((await caseDeLaLigne(2)).textContent).toBe('9')
    const grille = await screen.findByRole('list')
    expect(grille.querySelector('.saisie__somme')?.textContent).toBe('27')
  })

  it('toucher une case remplie la corrige à la frappe suivante, sans perdre les autres', async () => {
    monter()
    await userEvent.click(await caseDeLaLigne(1))
    for (const zone of ['10', '9', '8']) {
      await userEvent.click(screen.getByRole('button', { name: zone }))
    }

    await userEvent.click(await caseDeLaLigne(2))
    await userEvent.click(screen.getByRole('button', { name: 'M' }))

    expect((await caseDeLaLigne(1)).textContent).toBe('10')
    expect((await caseDeLaLigne(2)).textContent).toBe('M')
    expect((await caseDeLaLigne(3)).textContent).toBe('8')
  })
})

// Revue d'E17US011 — les scénarios qu'aucun test ne montait : la ligne et le pavé sur deux volées
// différentes (axes B, C1, D), une cible à plusieurs archers (B), un barème illisible (B, C1, C2,
// D), une série en chargement (D). Oracle : planche S02, la case marquée est celle que la
// prochaine frappe remplit.
describe('Saisie — la ligne montre la volée que le pavé ouvre', () => {
  const MARTIN = { ...LIGNE, position: 'B', archer_id: 13, nom: 'MARTIN', prenom: 'Paul' }

  beforeEach(() => {
    erreurSaisie = null
    SERIE = SERIE_VIDE
    GRILLE = GRILLE_SERVIE
    BAREME = BAREME_SERVI
    SERIE_CHARGEE = true
  })

  async function caseDe(nom: string, numero: number) {
    const grille = await screen.findByRole('list')
    return within(grille).getByRole('button', { name: new RegExp(`^Flèche ${numero} de ${nom}`) })
  }

  async function taper(...zones: string[]) {
    const pave = screen.getByRole('group', { name: 'Volées' }).parentElement as HTMLElement
    for (const zone of zones) {
      await userEvent.click(within(pave).getByRole('button', { name: zone }))
    }
  }

  it('choisir une volée au navigateur : la ligne la montre, avec ses valeurs', async () => {
    SERIE = { ...SERIE_VIDE, volees: [volee(1, ['10', '9', '8'])] }
    monter()
    await userEvent.click(await caseDe('DURAND', 1))

    await userEvent.click(
      within(screen.getByRole('group', { name: 'Volées' })).getByRole('button', { name: /^1/ }),
    )

    expect((await caseDe('DURAND', 1)).textContent).toBe('10')
    expect((await caseDe('DURAND', 3)).textContent).toBe('8')
  })

  it('deux archers : la frappe va à celui dont on a touché la case', async () => {
    GRILLE = { ...GRILLE_SERVIE, data: [LIGNE, MARTIN] }
    monter()
    await userEvent.click(await caseDe('DURAND', 1))
    await taper('10')

    await userEvent.click(await caseDe('MARTIN', 1))
    await taper('9')

    expect((await caseDe('MARTIN', 1)).textContent).toBe('9')
    expect((await caseDe('DURAND', 1)).textContent).toBe('10')
    expect((await caseDe('DURAND', 2)).textContent).toBe('')
  })

  it('une flèche visée ne survit pas à un changement d’archer par son nom', async () => {
    GRILLE = { ...GRILLE_SERVIE, data: [LIGNE, MARTIN] }
    monter()
    await userEvent.click(await caseDe('DURAND', 1))
    await taper('10', '9', '8')
    await userEvent.click(await caseDe('DURAND', 2))

    const grille = await screen.findByRole('list')
    await userEvent.click(within(grille).getByRole('button', { name: /MARTIN.*volées/ }))
    await userEvent.click(within(grille).getByRole('button', { name: /DURAND.*volées/ }))
    await taper('M')

    // Volée pleine, plus rien de visé : la frappe est refusée, la flèche 2 reste un 9.
    expect((await caseDe('DURAND', 2)).textContent).toBe('9')
  })

  it('tant que la série n’est pas chargée, les cases ne s’actionnent pas', async () => {
    SERIE_CHARGEE = false
    monter()

    expect(await caseDe('DURAND', 1)).toBeDisabled()
  })

  it('un barème illisible s’affiche « ? », jamais comme un zéro', async () => {
    BAREME = { data: undefined, isError: true, isSuccess: false }
    SERIE = { ...SERIE_VIDE, volees: [volee(1, ['10', '9', '8'])] }
    monter()

    expect(await cumulAffiche()).toBe('?')
  })

  it('la case marquée est celle que la prochaine frappe remplit', async () => {
    monter()
    await userEvent.click(await caseDe('DURAND', 1))
    await taper('10', '9', '8')
    await userEvent.click(await caseDe('DURAND', 2))

    const marquees = [1, 2, 3].map(async (n) =>
      (await caseDe('DURAND', n)).classList.contains('saisie__case--en-cours'),
    )
    expect(await Promise.all(marquees)).toEqual([false, true, false])
  })
})
