// Tests de **montage** de la table de classement (E06US001, élargie par E16US004).
//
// Ce fichier naît d'un défaut de **conjonction** trouvé en revue, du genre que ni les tests de
// logique pure ni ceux d'architecture ne voient : `centrerLignes` filtrait correctement et
// `totauxExAequo` calculait correctement, mais branchés l'un sur l'autre ils **effaçaient une
// égalité FFTA** — le calcul recevait la liste déjà filtrée, donc un archer suivi à 542 à égalité
// avec un **non suivi** se retrouvait seul avec son total. D'où la règle que ces tests verrouillent
// : **la source du calcul n'est pas la source de l'affichage**.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDeroule } from '../suivi/deroule'
import type { LigneClassement } from './api'
import { __reinitialiserCumulsDePage_TESTS } from '../../shared/ui/pagination'
import { TableClassement } from './TableClassement'

// ⚠️ On mocke **le hook**, pas `getDeroule` : `useDeroule` appelle la fonction par sa liaison
// **locale** au module, que le remplacement de l'export ne redirige pas — la vraie requête partait
// donc quand même, et le test lisait « connexion perdue ».
vi.mock('../suivi/deroule', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../suivi/deroule')>()),
  useDeroule: vi.fn(),
}))

// `LigneArcher` monte `usePlacerArcher` même en lecture seule : il faut un client, même inutilisé.
function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

function ligne(patch: Partial<LigneClassement> = {}): LigneClassement {
  return {
    rang_scratch: 23,
    rang_categorie: 5,
    archer_id: 1,
    nom: 'MARTIN',
    prenom: 'Luc',
    categorie_id: 3,
    categorie_libelle: 'Senior 1 Homme',
    cible: 7,
    club_id: 2,
    total: 542,
    nb_dix: 12,
    nb_neuf: 9,
    statut: 'en_lice',
    ...patch,
  }
}

// L'archer avec qui l'égalité existe : même catégorie, même total, un autre identifiant.
const RIVAL = ligne({ archer_id: 2, nom: 'DURAND', prenom: 'Eve', rang_scratch: 24, nb_dix: 8 })

describe('TableClassement — ex æquo et liste centrée', () => {
  it('signale l’ex æquo même quand l’archer à égalité est masqué par le centrage', () => {
    // Le cas réel : je suis MARTIN, pas DURAND. L'écran ne montre que MARTIN — mais son 542 est
    // toujours à égalité avec celui de DURAND, et le taire trompe sur la solidité de son rang.
    render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={[ligne()]}
            lignesCompletes={[ligne(), RIVAL]}
            admin={false}
          />
        }
      />,
    )

    expect(screen.getByText(/Ex æquo signalés/)).toBeInTheDocument()
  })

  it('ne signale rien quand l’égalité n’existe pas dans la liste complète', () => {
    // Symétrique indispensable : sans lui, le test précédent passerait aussi avec un composant qui
    // affiche la mention en permanence.
    render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={[ligne()]}
            lignesCompletes={[ligne(), ligne({ archer_id: 2, total: 500 })]}
            admin={false}
          />
        }
      />,
    )

    expect(screen.queryByText(/Ex æquo signalés/)).toBeNull()
  })

  it('n’annonce pas la règle quand l’égalité ne concerne aucune ligne affichée', () => {
    // ⚠️ Le piège du correctif lui-même (2ᵉ passe de revue). Calculer les égalités sur la liste
    // complète corrige le **marquage**, mais si l'on en déduit aussi l'**affichage** du paragraphe
    // de règle, celui-ci apparaît dès qu'une égalité existe quelque part dans le créneau — donc
    // quasiment en permanence — sous une table de trois lignes dont aucune n'est marquée.
    // `departage.ts` l'énonce : « encore faut-il montrer sur qui ».
    render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={[ligne()]}
            lignesCompletes={[
              ligne(),
              ligne({ archer_id: 2, total: 500 }),
              ligne({ archer_id: 3, total: 500 }),
            ]}
            admin={false}
          />
        }
      />,
    )

    // L'égalité existe (500 = 500) mais entre deux archers qu'on n'affiche pas : rien à annoncer.
    expect(screen.queryByText(/Ex æquo signalés/)).toBeNull()
  })

  it('se comporte comme avant quand aucune liste complète n’est fournie', () => {
    // Non-régression des appelants qui n'ont rien à centrer (admin, simulation, écran de salle) :
    // `lignesCompletes` est optionnelle et retombe sur `lignes`.
    render(
      <Cadre enfants={<TableClassement tournoiId={1} lignes={[ligne(), RIVAL]} admin={false} />} />,
    )

    expect(screen.getByText(/Ex æquo signalés/)).toBeInTheDocument()
  })
})

describe('TableClassement — détail des flèches (CA racine E16US004)', () => {
  beforeEach(() => {
    vi.mocked(useDeroule).mockReturnValue({
      data: {
        tournoi_id: 1,
        archer_id: 1,
        cumul: 542,
        volees: [
          { numero: 1, valeurs: ['10', '9', '9'], points: 28, statut: 'valide', horodatage: null },
        ],
      },
      isPending: false,
      isError: false,
      // Double cast **assumé** (règle 4-front) : le type de retour de React Query compte une
      // trentaine de champs dont aucun n'intervient ici. Les stubber tous rendrait le test moins
      // lisible sans rien prouver de plus ; c'est un double de test, pas une valeur de production.
    } as unknown as ReturnType<typeof useDeroule>)
  })

  it('déplie le détail au clavier et l’annonce au lecteur d’écran', async () => {
    // P03 demandait « le détail des flèches des autres » — réponse *« oui »*. C'est le livrable le
    // plus visible de l'US, et il n'avait aucun test : ~130 lignes de JSX, dont le contrat
    // d'accessibilité (`aria-expanded`, `aria-controls`) que rien ne vérifiait.
    //
    // Au **clavier**, délibérément : l'appli publique se consulte aussi au lecteur d'écran, et
    // c'est la raison invoquée pour préférer un vrai `<button>` à une rangée cliquable. Tester au
    // clic seul aurait laissé passer une régression vers `<tr onClick>`.
    const utilisateur = userEvent.setup()
    render(
      <Cadre
        enfants={<TableClassement tournoiId={1} lignes={[ligne()]} admin={false} detailFleches />}
      />,
    )

    const bascule = screen.getByRole('button', { name: /MARTIN/ })
    expect(bascule).toHaveAttribute('aria-expanded', 'false')

    bascule.focus()
    await utilisateur.keyboard('{Enter}')

    expect(bascule).toHaveAttribute('aria-expanded', 'true')
    await waitFor(() => expect(screen.getByText(/10 9 9/)).toBeInTheDocument())
    // La région dépliée est bien celle que le bouton déclare piloter.
    expect(bascule.getAttribute('aria-controls')).toBe(`detail-archer-${ligne().archer_id}`)

    await utilisateur.keyboard('{Enter}')
    expect(bascule).toHaveAttribute('aria-expanded', 'false')
  })

  it('n’expose aucun dépliant quand le détail n’est pas demandé', async () => {
    // L'admin a l'écran de saisie et la salle « aucune interaction » (CA E07US004) : la prop est
    // réservée à l'appli publique, et son défaut doit rester inerte.
    render(<Cadre enfants={<TableClassement tournoiId={1} lignes={[ligne()]} admin={false} />} />)

    expect(screen.queryByRole('button', { name: /MARTIN/ })).toBeNull()
  })
})

// --- Le classement projeté, page après page (E16US009, ADR-0098) --------------------------------
//
// ⚠️ **Un test de rendu par écran** — la leçon de `DETTE-085`, apprise à ses dépens dans l'US
// précédente : `tsc` ne voit pas une propriété fournie et jamais consommée, et aucun test ne montait
// l'écran concerné. Le composant calculait ses repères et ne les rendait pas. Ces deux tests-ci
// tombent si `pagination` cesse d'être honorée, dans un sens comme dans l'autre.

describe('TableClassement — le reste projeté', () => {
  // Dix archers : trois en tête figée, sept dans le reste, découpé en pages de quatre → deux pages.
  const DIX = Array.from({ length: 10 }, (_, i) =>
    ligne({ archer_id: i + 1, nom: `ARCHER${i}`, rang_scratch: i + 1, total: 600 - i }),
  )
  // ⚠️ **12 noms réglés donnent 4 LIGNES par page**, pas 12 : le réglage compte des noms tels que la
  // page d'affectations les dispose — sur trois colonnes CSS — et le classement est un tableau
  // mono-colonne. Bloquant de revue : à valeur brute, le bas de chaque page tombait sous le bord de
  // l'image, sur un écran où personne ne peut faire défiler.
  const REGLAGE = { noms_par_page: 12, cadence_page_s: 20 }

  // Le cumul de `useSecondesDAffichage` lit `Date.now()` et vit **au module**, donc il persiste
  // d'un test à l'autre dans ce fichier : sans horloge figée, ces assertions vérifieraient surtout
  // que la suite tourne vite. Oracle maîtrisé (règle 9) — relevé en revue.
  beforeEach(() => {
    vi.useFakeTimers()
    // ⚠️ **Indispensable, et le trou avait été fermé dans l'AUTRE fichier.** `useSecondesDAffichage`
    // écrit son cumul **au démontage**, dans une `Map` de module partagée par tous les tests de ce
    // fichier. L'`afterEach` local (`useRealTimers`) s'exécutant AVANT le `cleanup` de RTL, ce
    // cumul est écrit avec une horloge **réelle** : chaque montage paginé y laisse la durée réelle
    // du test. L'oracle du test de cadence est un `floor(t / 5)` — il suffit qu'une seconde traîne
    // pour qu'il tombe en CI. Vert ici, rouge un jour, diagnostic trompeur (3ᵉ passe, trois axes).
    __reinitialiserCumulsDePage_TESTS()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('rend UNE page du reste, avec son compteur, et laisse la suite hors écran', () => {
    const { container } = render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={DIX}
            admin={false}
            teteFigee={3}
            pagination={REGLAGE}
          />
        }
      />,
    )

    // La tête : toujours là, quelle que soit la page.
    expect(container.textContent).toContain('ARCHER0 ')
    // Page 1 du reste : les archers 3 à 6.
    expect(container.textContent).toContain('ARCHER3 ')
    expect(container.textContent).toContain('ARCHER6 ')
    // Page 2 : pas encore à l'écran — c'est ce qui distingue une pagination d'un rendu complet.
    expect(container.textContent).not.toContain('ARCHER7 ')
    // Le compteur de pages, que P06 demande explicitement (« oui pour le compteur de pages »).
    expect(container.querySelector('.salle-pages__compteur')).not.toBeNull()
  })

  it('convertit les NOMS réglés en LIGNES de tableau, sans quoi la page déborde de l’écran', () => {
    // ⚠️ **Le bloquant de la revue d'E16US009**, au réglage livré par défaut. `noms_par_page`
    // compte des noms tels que `columns: 3 22ch` les dispose — trois colonnes —, alors que le
    // classement est un tableau **mono-colonne** : 40 noms y feraient 40 lignes, trois fois la
    // hauteur d'un 1920×1080, et `.classement__pages` n'a **aucun ascenseur** (ADR-0098 §3). Le bas
    // de page n'aurait pas été « mal lu », il n'aurait **jamais été montré**. Ce test est l'oracle
    // du ratio : 12 noms réglés → 4 lignes par page ; sans la conversion, `nombreDePages(7, 12)`
    // vaudrait 1.
    const { container } = render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={DIX}
            admin={false}
            teteFigee={3}
            pagination={REGLAGE}
          />
        }
      />,
    )

    // 7 lignes de reste découpées par 4 → deux pages, donc un compteur « 1/2 ».
    // `toBe` et non `toContain` : ce dernier acceptait aussi « /12 », « /20 », « /25 ».
    expect(container.querySelector('.salle-pages__compteur-total')?.textContent).toBe('/2')
    // La 4ᵉ ligne du reste est la dernière de la page 1 ; la 5ᵉ attend son tour.
    expect(container.textContent).toContain('ARCHER6 ')
    expect(container.textContent).not.toContain('ARCHER7 ')
  })

  it.each([
    // [noms réglés, lignes attendues par page] — les deux bornes du domaine, le défaut livré, et
    // **le point de bascule** entre les deux constantes.
    [5, 2], // plancher : `ceil(5/3)` = 2, et non 1 — c'est `ceil` qui est prouvé ici, pas `floor`
    [12, 4], // le point nominal des tests voisins
    [24, 8], // ratio seul : le plafond n'a pas encore mordu
    [27, 9], // ⚠️ le point de BASCULE exact — au-delà, le réglage n'agit plus sur le classement
    [40, 9], // ⚠️ le DÉFAUT LIVRÉ : `ceil(40/3)` = 14, plafonné à `LIGNES_PROJETEES_MAX`
    [100, 9], // plafond du domaine : idem, le plafond d'affichage tient
  ])('découpe %i noms réglés en pages de %i lignes', (noms, lignesAttendues) => {
    // ⚠️ **Le résidu que la 2ᵉ passe a trouvé, et pourquoi il y a DEUX constantes.** Le ratio ferme
    // le facteur ×3 ; restent un chrome fixe (tête figée + en-têtes, qui ne se divise pas) et un
    // écart de hauteur de ligne qui *croît* quand l'écran rétrécit — à 1280×720, le défaut livré
    // débordait encore de deux lignes. Le plafond ne rend pas la valeur juste (rien n'a été mesuré
    // sur un vidéoprojecteur), il rend la **direction de l'erreur** sûre : trop de pages plutôt que
    // des archers jamais montrés.
    const TRENTE = Array.from({ length: 30 }, (_, i) =>
      ligne({ archer_id: i + 1, nom: `ARCHER${i}`, rang_scratch: i + 1, total: 700 - i }),
    )
    const { container } = render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={TRENTE}
            admin={false}
            teteFigee={3}
            pagination={{ noms_par_page: noms, cadence_page_s: 20 }}
          />
        }
      />,
    )

    // ⚠️ **On compte les RANGÉES rendues, pas seulement les pages.** Le compteur seul ne borne pas
    // la valeur : `ceil(27/x)` vaut 3 pour tout `x` de 9 à 13, si bien qu'une dérive de ±1 du
    // plafond passait inaperçue — alors que « jamais plus de N » est précisément ce que la fiche,
    // le journal et l'aide d'admin annoncent à l'organisateur (3ᵉ passe, axes B et D).
    expect(container.querySelectorAll('.classement__pages tbody tr')).toHaveLength(
      Math.min(lignesAttendues, 27),
    )
    const attendu = Math.ceil(27 / lignesAttendues)
    expect(container.querySelector('.salle-pages__compteur-total')?.textContent).toBe(`/${attendu}`)
  })

  it('tourne au rythme RÉGLÉ, et non au défaut du module', () => {
    // ⚠️ **La moitié « cadence » du CA n'était prouvée par aucun test** (relevé en 2ᵉ passe, axe B) :
    // toutes les fixtures valaient 20, c'est-à-dire `SECONDES_PAR_PAGE`. Remplacer
    // `pagination.cadence_page_s` par la constante du module laissait la suite entière verte —
    // alors que « 20 s **(réglable)** » est la demande même du questionnaire P06.
    const REGLAGE_RAPIDE = { noms_par_page: 12, cadence_page_s: 5 }
    const { container } = render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={DIX}
            admin={false}
            teteFigee={3}
            pagination={REGLAGE_RAPIDE}
          />
        }
      />,
    )

    // Sous la cadence réglée : encore en page 1. (Assertion appariée — sans elle, le cas suivant
    // passerait aussi avec un composant qui tourne à chaque battement.)
    act(() => {
      vi.advanceTimersByTime(4_000)
    })
    expect(container.textContent).toContain('ARCHER3 ')
    expect(container.textContent).not.toContain('ARCHER7 ')

    // Passé la cadence réglée : page 2. Avec 20 s en dur, rien n'aurait bougé.
    act(() => {
      vi.advanceTimersByTime(2_000)
    })
    expect(container.textContent).toContain('ARCHER7 ')
    expect(container.textContent).not.toContain('ARCHER3 ')

    // Et la séquence **boucle** : c'est la promesse « tout archer finit par apparaître ».
    act(() => {
      vi.advanceTimersByTime(5_000)
    })
    expect(container.textContent).toContain('ARCHER3 ')
  })

  it('n’enferme JAMAIS le reste dans un cadre à ascenseur quand il est projeté', () => {
    // ⚠️ Le cœur d'ADR-0098 : sur un vidéoprojecteur, `overflow-y: auto` produit un cadre que
    // personne ne peut actionner. Ce test tombe si quelqu'un « simplifie » en réunifiant les deux
    // branches de rendu — et la salle perdrait alors tout ce qui suit la 3ᵉ ligne.
    const { container } = render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={DIX}
            admin={false}
            teteFigee={3}
            pagination={REGLAGE}
          />
        }
      />,
    )

    expect(container.querySelector('.classement__defilement')).toBeNull()
    expect(container.querySelector('.classement__pages')).not.toBeNull()
  })

  it('garde le cadre à ascenseur sur une surface qu’on manipule', () => {
    // L'assertion **appariée** de la précédente : sans réglage de pages, rien ne change pour le PC
    // d'organisation — l'ascenseur y est le bon geste, et cette US ne devait rien y toucher.
    const { container } = render(
      <Cadre
        enfants={<TableClassement tournoiId={1} lignes={DIX} admin={false} teteFigee={3} />}
      />,
    )

    expect(container.querySelector('.classement__defilement')).not.toBeNull()
    expect(container.querySelector('.classement__pages')).toBeNull()
    // Et **tout le monde** est rendu : le cadre défile, il ne tronque pas.
    expect(container.textContent).toContain('ARCHER9 ')
  })
})
