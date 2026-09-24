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
import { Saisie } from './Saisie'

const LIGNE = {
  position: 'A',
  archer_id: 12,
  nom: 'DURAND',
  prenom: 'Léa',
  zones: ['10', '9', '8', 'M'],
  forfait: false,
}

function volee(numero: number, valeurs: string[], extra: Record<string, unknown> = {}) {
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

// ⚠️ **Mutable, et remise à zéro à chaque cas.** Le défaut que cette US corrige vivait dans le
// **consommateur** (`LigneArcher` lisait `serie.cumul`), pas dans une fonction pure : le prouver
// demande de faire diverger `cumul` et `volees`, donc de poser la série cas par cas.
let SERIE: Record<string, unknown> = { archer_id: 12, cumul: 0, volees: [], grain: null }

let erreurSaisie: Error | null = null

vi.mock('./hooks', () => ({
  useRejeuFileHorsLigne: () => undefined,
  useGrille: () => ({ data: [LIGNE], isError: false, isSuccess: true, error: null }),
  useBareme: () => ({ data: { nb_volees: 2, nb_fleches_par_volee: 3 } }),
  useGrain: () => ({ data: null }),
  useDeparts: () => ({ data: [], isSuccess: true }),
  useFixerDepart: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  useSerie: () => ({ data: SERIE, isError: false, isSuccess: true, error: null }),
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
  await userEvent.click(within(grille).getByRole('button'))
}

describe('Saisie — un refus de préséance est expliqué', () => {
  // ⚠️ Sans cette remise à zéro, un cas qui oublierait d'affecter `erreurSaisie` hériterait
  // silencieusement de l'erreur du précédent et passerait pour la mauvaise raison : la suite
  // serait verte par ordre d'exécution, pas par construction.
  beforeEach(() => {
    erreurSaisie = null
    SERIE = { archer_id: 12, cumul: 0, volees: [], grain: null }
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
    await userEvent.click(within(grille).getByRole('button'))
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
    SERIE = { archer_id: 12, cumul: 0, volees: [], grain: null }
  })

  // ⚠️ **Le test doit vivre ICI, pas seulement dans `volees.test.ts`.** Le défaut n'était pas dans
  // `cumulSaisi` — qui n'existait pas — mais dans `LigneArcher`, qui lisait `serie.cumul`. Les
  // tests de la fonction pure resteraient **tous verts** si quelqu'un remettait `serie.cumul` au
  // rendu. C'est le motif de `DETTE-085`, que l'en-tête de ce fichier cite déjà.
  //
  // Oracle : questionnaire `s02-poste-de-cible.md`, question 3 — « en permanence, c'est un bon
  // rappel sur la cible ». Avec le grain « fin de série », le serveur rend 0 tout au long.
  it('affiche 54 là où le serveur rend un cumul de 0', async () => {
    SERIE = {
      archer_id: 12,
      cumul: 0,
      volees: [volee(1, ['10', '9', '8']), volee(2, ['9', '9', '9'])],
      grain: null,
    }
    monter()

    // ⚠️ Viser le **cumul**, pas un `getByText` : « 27 » figure aussi dans la bande de relecture,
    // comme total de volée. Un `getByText` ambigu ferait échouer le test pour la mauvaise raison.
    expect(await cumulAffiche()).toBe('54')
  })

  it('compte une volée partie hors ligne, que le serveur ignore encore', async () => {
    // La garantie d'E04US009, et la justification écrite de `DETTE-111` : le poste doit valoriser
    // ce que le serveur n'a **jamais reçu**. `serieOptimiste` ajoute la volée à `volees` sans
    // toucher `cumul` — si le rendu lisait `cumul`, le marqueur verrait 0 pendant la coupure.
    SERIE = {
      archer_id: 12,
      cumul: 0,
      volees: [volee(1, ['10', '9', '8'], { en_attente: true })],
      grain: null,
    }
    monter()

    expect(await cumulAffiche()).toBe('27')
  })

  it('compte une volée rendue en correction, alignement sur ADR-0109', async () => {
    // Côté serveur, une volée en correction **compte toujours** : son score tient. Le front doit
    // dire la même chose, sans quoi le total chuterait à l'instant du renvoi par le scoreur.
    SERIE = {
      archer_id: 12,
      cumul: 0,
      volees: [volee(1, ['10', '9', '8'], { en_correction: true, validee_par: 'MOREAU' })],
      grain: null,
    }
    monter()

    expect(await cumulAffiche()).toBe('27')
  })
})
