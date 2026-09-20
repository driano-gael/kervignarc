// Rendu du cockpit de simulation — le test qui manquait quand son contrat a changé (E06US009).
//
// ⚠️ **Pourquoi ce fichier existe.** `EtatSession` est un miroir écrit à la main d'un modèle
// Pydantic, et `fetchJson<T>` transtype sans valider (`DETTE-108`) : quand E06US009 a changé le
// contrat, `tsc` est resté vert, `vitest` aussi (zéro test ici) et la porte a rendu 14/14 — sur une
// appli admin qui tombait en page blanche, faute d'`ErrorBoundary`. ⚠️ **Le décor est typé sans
// transtypage** : un `as unknown as` y rejouerait le défaut que ce test garde (revue, 2ᵉ passe).

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Classement, LigneClassement } from '../competition/api'
import type { CreneauSimule, EtatSession, TableauSimule } from './api'
import { Simulation } from './Simulation'

vi.mock('../../shared/realtime/RealtimeClient', () => ({
  RealtimeClient: class {
    connecter() {}
    fermer() {}
  },
}))

const mutationInerte = { mutate: vi.fn(), isPending: false, error: null }

vi.mock('./hooks', async () => {
  const reel = await vi.importActual<typeof import('./hooks')>('./hooks')
  return {
    ...reel,
    useEtatSimulation: vi.fn(),
    useDemarrerSimulation: vi.fn(),
    useDetailArcher: () => ({ data: undefined }),
    useAvancer: () => mutationInerte,
    useTerminer: () => mutationInerte,
    usePause: () => mutationInerte,
    useReprendre: () => mutationInerte,
    useSaisirVolee: () => mutationInerte,
    useDesignerVainqueur: () => mutationInerte,
  }
})

const { useDemarrerSimulation, useEtatSimulation } = await import('./hooks')

function ligne(archerId: number, nom: string, total: number): LigneClassement {
  return {
    rang_scratch: 1,
    rang_categorie: 1,
    archer_id: archerId,
    nom,
    prenom: 'P',
    categorie_id: 3,
    categorie_libelle: 'Senior 1 Homme',
    cible: null,
    club_id: null,
    total,
    nb_dix: 0,
    nb_neuf: 0,
    statut: 'en_lice',
  }
}

function classement(departId: number, lignes: LigneClassement[]): Classement {
  return { depart_id: departId, lignes, egalites_a_departager: [] }
}

/** Un arbre — de quoi distinguer « ce créneau duelle » de « pas encore ». */
const ARBRE: TableauSimule = {
  effectif: 2,
  taille: 2,
  nb_tours: 1,
  est_termine: false,
  duels: [],
  podium: [],
}

function etatA(creneaux: CreneauSimule[]): EtatSession {
  return {
    session_id: 7,
    tournoi_id: 1,
    tournoi_nom: 'Salle 18m',
    graine: 42,
    etat_pilote: 'en_pause',
    etape: 'qualification',
    progression: { volees_faites: 1, volees_total: 4, duels_faits: 0, duels_total: 0 },
    creneaux,
    prochaine_unite: null,
  }
}

/** Deux créneaux **réellement peuplés** : à un seul, « le premier partout » resterait invisible. */
const MATIN: CreneauSimule = {
  depart_id: 41,
  libelle: 'Départ n°1 — 09:00',
  classement: classement(41, [ligne(1, 'MARTIN', 30)]),
  tableaux: [],
}

const APRES_MIDI: CreneauSimule = {
  depart_id: 42,
  libelle: 'Départ n°2 — 14:00',
  classement: classement(42, [ligne(2, 'CADIOU', 28)]),
  tableaux: [],
}

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

/** Ouvre le cockpit : le composant n'expose pas sa session, on passe donc par le vrai geste. */
async function ouvrirLeCockpit(etat: EtatSession) {
  vi.mocked(useEtatSimulation).mockReturnValue({ data: etat } as ReturnType<
    typeof useEtatSimulation
  >)
  vi.mocked(useDemarrerSimulation).mockReturnValue({
    mutate: (_entree: unknown, options?: { onSuccess?: (etat: EtatSession) => void }) =>
      options?.onSuccess?.(etat),
    isPending: false,
    error: null,
  } as unknown as ReturnType<typeof useDemarrerSimulation>)
  render(<Cadre enfants={<Simulation tournoiId={1} />} />)
  await userEvent.click(screen.getByRole('button', { name: /Démarrer la simulation/ }))
}

describe('Simulation — le cockpit rejoue chaque créneau (E06US009)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('rend un classement par créneau, titré de son libellé', async () => {
    await ouvrirLeCockpit(etatA([MATIN, APRES_MIDI]))

    // ⚠️ L'assertion porte sur les DEUX archers : un cockpit resté sur « le » premier créneau
    // afficherait MARTIN seul, et un test qui ne compterait que les titres le laisserait passer.
    expect(screen.getByLabelText('Classement — Départ n°1 — 09:00')).toBeInTheDocument()
    expect(screen.getByLabelText('Classement — Départ n°2 — 14:00')).toBeInTheDocument()
    // `TableClassement` compose « NOM Prénom » dans un seul nœud — d'où le motif, pas l'égalité.
    expect(screen.getByText(/MARTIN/)).toBeInTheDocument()
    expect(screen.getByText(/CADIOU/)).toBeInTheDocument()
  })

  it('groupe le sélecteur d’archers par créneau dans la vue « Archer »', async () => {
    // ⚠️ **Cette vue n'est pas celle par défaut** : le cockpit monte « Public », et la 1ʳᵉ version
    // de ce fichier ne cliquait aucun onglet — deux des trois vues migrées n'étaient donc jamais
    // rendues (relevé en 2ᵉ passe par trois axes).
    await ouvrirLeCockpit(etatA([MATIN, APRES_MIDI]))
    await userEvent.click(screen.getByRole('button', { name: 'Archer' }))

    expect(screen.getAllByRole('group').map((g) => g.getAttribute('label'))).toEqual([
      'Départ n°1 — 09:00',
      'Départ n°2 — 14:00',
    ])
    expect(screen.getByRole('option', { name: /MARTIN P — 30 pts/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /CADIOU P — 28 pts/ })).toBeInTheDocument()
  })

  it('ne propose qu’une entrée pour un archer inscrit sur deux créneaux', async () => {
    // ⚠️ Cas soutenu du projet (`DETTE-046`). Deux `<option>` de même `value` faisaient
    // re-sélectionner la première par le navigateur : cliquer « Départ n°2 » affichait
    // « Départ n°1 ». Le détail se charge par `archer_id` seul, les deux étaient équivalentes.
    const doubleInscrit = { ...APRES_MIDI, classement: classement(42, [ligne(1, 'MARTIN', 0)]) }
    await ouvrirLeCockpit(etatA([MATIN, doubleInscrit]))
    await userEvent.click(screen.getByRole('button', { name: 'Archer' }))

    expect(screen.getAllByRole('option', { name: /MARTIN/ })).toHaveLength(1)
  })

  it('dit quel créneau n’a pas commencé sans taire celui qui duelle', async () => {
    // ⚠️ La garde est passée de `etat.tableaux.length === 0` à `creneaux.every(...)` : c'est la
    // seule LOGIQUE neuve du correctif, et elle n'était exercée nulle part — le décor d'origine
    // portait `tableaux: []` partout, donc la branche non vide n'était jamais prise.
    await ouvrirLeCockpit(etatA([{ ...MATIN, tableaux: [ARBRE] }, APRES_MIDI]))
    await userEvent.click(screen.getByRole('button', { name: 'Scoreur' }))

    expect(screen.queryByText("Les duels n'ont pas encore commencé.")).not.toBeInTheDocument()
    expect(screen.getByText(/pas encore commencé sur ce créneau/)).toBeInTheDocument()
    expect(screen.getByLabelText('Duels — Départ n°1 — 09:00')).toBeInTheDocument()
  })

  it('ne dit « les duels n’ont pas commencé » que si AUCUN créneau ne duelle', async () => {
    await ouvrirLeCockpit(etatA([MATIN, APRES_MIDI]))
    await userEvent.click(screen.getByRole('button', { name: 'Scoreur' }))

    expect(screen.getByText("Les duels n'ont pas encore commencé.")).toBeInTheDocument()
    expect(screen.queryByText(/pas encore commencé sur ce créneau/)).not.toBeInTheDocument()
  })
})
