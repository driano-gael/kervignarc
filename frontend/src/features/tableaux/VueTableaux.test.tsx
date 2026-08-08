// Tests de **montage** de la vue publique des tableaux (E07US005).
//
// Ce fichier existe à cause d'un défaut précis, et il vaut mieux le dire que le paraphraser : la
// première version de `VueTableaux` dérivait la liste des archers suivis **dans le sélecteur
// Zustand** (`s.suivis.filter(...).map(...)`). Un sélecteur qui rend un tableau neuf à chaque appel
// rend `getSnapshot` instable pour `useSyncExternalStore` — donc **boucle de rendu infinie** en
// Zustand v5 / React 19, y compris avec zéro archer suivi. La fonctionnalité était inutilisable, et
// **aucune porte mécanique ne pouvait le voir** : ni `tsc`, ni `eslint`, ni les 17 tests de logique
// pure de `presentation.test.ts`, qui n'appellent jamais React.
//
// Le dépôt portait pourtant déjà le correctif, sur le **même store**, dans la feature voisine
// (`suivi/VueSuivi.tsx`, « correctif de revue A »). Ce qui manquait n'était pas la connaissance,
// c'était un test qui **monte le composant**. C'est tout l'objet de ce fichier — et la leçon
// réutilisable : une feature front sans un seul rendu testé a un angle mort de cette taille.
//
// ⚠️ **Depuis E16US004, cette vue ne lit plus le store du tout** : les archers suivis descendent en
// prop depuis `AccueilPublic`, comme le mode. Le piège du sélecteur instable n'a donc pas disparu,
// il a **changé d'adresse** — il vit maintenant chez le seul lecteur restant, couvert par
// `AccueilPublic.test.tsx`. Les tests ci-dessous gardent leur valeur (ils montent réellement la
// vue), mais ce n'est plus ici que se joue la boucle infinie.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Depart } from '../departs/api'
import { getDeparts } from '../departs/api'
import type { DuelPublic, TableauPublic, Tableaux } from './api'
import { getTableaux } from './api'
import { VueTableaux } from './VueTableaux'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getTableaux: vi.fn(),
}))

// Les arbres se lisent **par créneau** depuis ADR-0075 : la vue résout d'abord le départ en cours.
vi.mock('../departs/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/api')>()),
  getDeparts: vi.fn(),
}))

const _CRENEAU: Depart = {
  id: 41,
  tournoi_id: 1,
  numero: 1,
  horaire: '09:00',
  tarif_centimes: 800,
  quota: null,
  etat: 'ouvert',
}

function duel(patch: Partial<DuelPublic> = {}): DuelPublic {
  return {
    numero: 1,
    tour: 1,
    libelle: 'Demi-finale',
    place_en_jeu: null,
    plage: [1, 4],
    haut: { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' },
    bas: { archer_id: 2, nom: 'DURAND', prenom: 'Eve' },
    est_bye: false,
    points_haut: null,
    points_bas: null,
    vainqueur: null,
    termine: false,
    validee: false,
    ...patch,
  }
}

function reponse(duels: DuelPublic[] = [duel()]): Tableaux {
  const tableau: TableauPublic = {
    phase_id: 1,
    ordre: 2,
    type: 'elimination_directe',
    effectif: 4,
    taille: 4,
    nb_tours: 2,
    est_termine: false,
    duels,
    podium: [],
    // Non optionnel : le serveur sert toujours le champ (`null` quand l'arbre est monté).
    en_attente_de: null,
  }
  return { depart_id: 41, tableaux: [tableau] }
}

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

describe('VueTableaux — montage', () => {
  beforeEach(() => {
    vi.mocked(getTableaux).mockResolvedValue(reponse())
    vi.mocked(getDeparts).mockResolvedValue([_CRENEAU])
  })

  it('se monte et rend l’arbre sans boucler, sans aucun archer suivi', async () => {
    // Le cas le plus banal — et celui qui bouclait. `[].filter().map()` est déjà une référence
    // neuve : le défaut ne demandait même pas qu'on suive quelqu'un pour se déclencher.
    render(<Cadre enfants={<VueTableaux tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByText(/Demi-finale/)).toBeInTheDocument())
    expect(screen.getByText(/MARTIN/)).toBeInTheDocument()
  })

  it('annonce « en attente » plutôt que d’afficher un arbre que la compétition n’a pas décidé', async () => {
    // E05US024/ADR-0081. Une consolante « les rangs 5 à 8 du tableau », composée le matin : tant
    // que les quarts ne sont pas tirés, personne ne sait qui sont les rangs 5 à 8. Le serveur
    // renvoyait auparavant un arbre peuplé des 4 derniers **qualifiés** — bien formé, plausible et
    // faux —, puis, une fois le défaut vu, la phase disparaissait simplement de la liste.
    // Le spectateur doit lire ce qui manque, pas se demander où est passée la consolante.
    vi.mocked(getTableaux).mockResolvedValue({
      depart_id: 41,
      tableaux: [
        {
          phase_id: 7,
          ordre: 3,
          type: 'elimination_directe',
          effectif: 0,
          taille: 0,
          nb_tours: 0,
          est_termine: false,
          duels: [],
          podium: [],
          en_attente_de: 2,
        },
      ],
    })

    render(<Cadre enfants={<VueTableaux tournoiId={1} />} />)

    expect(await screen.findByText(/ne sont pas encore connues/)).toBeInTheDocument()
    // …et surtout **aucun** duel affiché : c'est le fond du correctif.
    expect(screen.queryByText('MARTIN')).not.toBeInTheDocument()
    // L'effectif à 0 ne doit pas s'afficher comme « 0 archers », qui se lirait comme un vide réel.
    expect(screen.queryByText(/0 archers/)).not.toBeInTheDocument()
  })

  it('rend « Mon chemin » quand l’affichage est centré sur les archers suivis', async () => {
    // ⚠️ **Comportement modifié en E16US004, volontairement.** Jusqu'ici la vue décidait seule
    // d'ouvrir sur « Mon chemin » dès qu'on suivait quelqu'un, et portait son propre sélecteur
    // « Mon chemin / Tableau complet ». Ce choix est remonté d'un cran : c'est l'interrupteur
    // « mes archers / tout » de l'en-tête public (P05) qui le porte, pour tout l'onglet à la fois.
    // Deux interrupteurs disant la même chose sur le même écran finissaient par se contredire.
    //
    // Le CA d'E07US005 — « la lecture *Mon chemin* est celle par défaut **dès qu'on suit
    // quelqu'un** » — n'est pas abandonné pour autant : il est porté par la valeur initiale de
    // `centrerSurSuivis` (armée), et c'est `AccueilPublic.test.tsx` qui le vérifie désormais, là où
    // le défaut se décide. Ici on teste la vue, qui ne fait qu'obéir à ses props.
    render(<Cadre enfants={<VueTableaux tournoiId={1} mode="suivis" suivis={[1]} />} />)

    await waitFor(() => expect(screen.getByText(/MARTIN/)).toBeInTheDocument())
    // En « mon chemin », c'est le nom de l'archer qui titre sa carte, pas un en-tête de tour.
    expect(screen.getByText('Luc MARTIN')).toBeInTheDocument()
  })

  it('rend l’arbre complet en affichage « tout », même en suivant un archer', async () => {
    render(<Cadre enfants={<VueTableaux tournoiId={1} suivis={[1]} />} />)

    // L'en-tête de branche est la signature de l'arbre complet ; « mon chemin » ne l'affiche pas.
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Demi-finale' })).toBeVisible())
  })

  it('dit « aucun de vos archers » plutôt que d’aligner des cartes sans nom', async () => {
    // Arbitrage (d) d'E16US004 : chaque vue distingue « aucun de vos archers ici » de son propre
    // vide. C'était la seule des cinq à ne pas le faire — elle rendait une carte « Archer suivi /
    // Pas engagé dans ce tableau » **par archer suivi**, toutes identiques et anonymes, sans jamais
    // proposer de revenir à l'affichage complet. Cas banal : on suit des archers d'une catégorie et
    // l'on regarde le tableau d'une autre.
    render(<Cadre enfants={<VueTableaux tournoiId={1} mode="suivis" suivis={[404, 405]} />} />)

    await waitFor(() =>
      expect(screen.getByText(/Aucun des archers que vous suivez/)).toBeInTheDocument(),
    )
    // Le recours est nommé, et aucune carte anonyme ne subsiste.
    expect(screen.getByText(/Tout le tournoi/)).toBeInTheDocument()
    expect(screen.queryByText('Archer suivi')).toBeNull()
  })

  it('en cas mixte, rend les engagés et compte les autres', async () => {
    // Un suivi engagé (1), un qui ne l'est pas (404) : on montre le premier et l'on dit que l'autre
    // manque — plutôt qu'une carte muette, le nom étant introuvable par construction (il se lit
    // dans les duels du tableau, où l'archer n'est pas).
    render(<Cadre enfants={<VueTableaux tournoiId={1} mode="suivis" suivis={[1, 404]} />} />)

    await waitFor(() => expect(screen.getByText('Luc MARTIN')).toBeInTheDocument())
    expect(screen.getByText(/Un autre archer suivi n’est pas engagé/)).toBeInTheDocument()
  })

  it('n’ouvre pas de requête et le dit quand aucun tableau n’existe', async () => {
    vi.mocked(getTableaux).mockResolvedValue({ depart_id: 41, tableaux: [] })

    render(<Cadre enfants={<VueTableaux tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByText(/Pas encore de tableau/)).toBeInTheDocument())
  })

  it('sur l’écran de salle, n’affiche aucune commande', async () => {
    // CA E07US004 : **aucune interaction** sur un écran projeté. Ni bascule de lecture, ni
    // sélecteur de phase — un bouton que personne ne peut actionner est un défaut, pas un détail.
    // `interactif={false}` verrouille l'arbre complet quoi qu'on lui passe : la salle ne suit
    // personne, et c'est ce verrou qu'on vérifie ici en lui donnant tout de même un suivi.
    render(
      <Cadre
        enfants={<VueTableaux tournoiId={1} interactif={false} mode="suivis" suivis={[1]} />}
      />,
    )

    await waitFor(() => expect(screen.getByText(/Demi-finale/)).toBeInTheDocument())
    expect(screen.queryByRole('button')).toBeNull()
    // Et c'est bien l'arbre complet qui s'affiche, pas « mon chemin » : personne ne suit d'archer
    // devant un projecteur.
    expect(screen.getByText(/MARTIN/)).toBeInTheDocument()
  })
})
