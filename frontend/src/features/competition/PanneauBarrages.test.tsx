// Test de **rendu** du panneau des barrages (E06US003).
//
// C'est le seul test de composant de cette feature, et il est là pour une raison précise : la revue
// a trouvé **trois fois de suite** le même mode de défaillance — une règle déplacée d'une couche
// (service, DTO, infra) sans que la couche qui la rend *observable par l'organisateur* suive. Deux
// bloquants sont nés exactement là :
//
// - un barrage **acté** disparaissait de l'écran (`filter(!clos)`), donc le correctif serveur qui
//   le rendait corrigeable ne servait personne — le juge ayant inversé deux flèches sur la dernière
//   place qualificative n'avait plus aucun chemin de réparation ;
// - un barrage **périmé** (le groupe d'ex æquo a changé depuis l'annonce) restait tirable et
//   actable : l'appli répondait « Départagé », acceptait la clôture, et le classement ne bougeait
//   pas d'un rang, sans un mot d'explication.
//
// Ni `tsc`, ni `eslint`, ni les 2523 tests backend, ni un test de logique pure ne pouvaient les
// voir : la faute est **dans le rendu**, entre un champ du DTO et ce que l'écran en fait. Tant
// qu'aucun test ne monte ce composant avec `clos: true` ou `perime: true`, le mode de défaillance
// reste invisible à la revue automatique — d'où ce fichier.
//
// On double **uniquement** les hooks de données (`./hooks`) : le JSX, lui, est celui de production.

import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { Barrage, LigneClassement } from './api'
import { PanneauBarrages } from './PanneauBarrages'

const mutation = { mutate: vi.fn(), isPending: false, isError: false, error: null }

vi.mock('./hooks', () => ({
  useBarrages: () => ({ data: barragesRendus }),
  useAnnoncerBarrage: () => mutation,
  useAnnulerBarrage: () => mutation,
  useCloreBarrage: () => mutation,
  useSaisirMancheBarrage: () => mutation,
}))

let barragesRendus: Barrage[] = []

const LIGNES: LigneClassement[] = [
  {
    rang_scratch: 2,
    rang_categorie: 2,
    archer_id: 1,
    nom: 'MARTIN',
    prenom: 'Alice',
    categorie_id: 1,
    categorie_libelle: 'Senior',
    cible: null,
    club_id: 1,
    total: 18,
    nb_dix: 1,
    nb_neuf: 0,
    statut: 'en_lice',
  },
  {
    rang_scratch: 2,
    rang_categorie: 2,
    archer_id: 2,
    nom: 'DURAND',
    prenom: 'Chloé',
    categorie_id: 1,
    categorie_libelle: 'Senior',
    cible: null,
    club_id: 1,
    total: 18,
    nb_dix: 1,
    nb_neuf: 0,
    statut: 'en_lice',
  },
]

function barrage(surcharge: Partial<Barrage> = {}): Barrage {
  return {
    id: 1,
    tournoi_id: 1,
    portee: 'qualification',
    rang_dispute: 2,
    reference: null,
    participants: [1, 2],
    manches: [
      [
        { archer_id: 1, score: 8, distance_au_centre: null },
        { archer_id: 2, score: 10, distance_au_centre: null },
      ],
    ],
    clos: false,
    est_resolu: true,
    ordre: [2, 1],
    groupes_a_rejouer: [],
    perime: false,
    incoherent: false,
    ...surcharge,
  }
}

function afficher(barrages: Barrage[], egalites: { rang: number; archer_ids: number[] }[] = []) {
  barragesRendus = barrages
  return render(<PanneauBarrages tournoiId={1} egalites={egalites} lignes={LIGNES} />)
}

describe('PanneauBarrages', () => {
  it('ne s’affiche pas quand il n’y a ni égalité signalée ni barrage', () => {
    // La promesse « aucun bruit par défaut » : l'étape 1 de la recette la vérifie à l'œil, et un
    // correctif l'avait cassée en logeant le départage manuel dans cette carte.
    const { container } = afficher([])
    expect(container).toBeEmptyDOMElement()
  })

  it('rend un barrage ACTÉ, avec de quoi le corriger et l’annuler', () => {
    // Le bloquant : `filter(!clos)` faisait disparaître le barrage au clic sur « Acter », donc le
    // seul chemin de réparation d'un verdict inversé.
    afficher([barrage({ clos: true })])

    expect(screen.getByText(/acté/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Corriger la manche 1/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Annuler ce barrage/ })).toBeInTheDocument()
    // …mais plus rien à acter : c'est déjà fait.
    expect(screen.queryByRole('button', { name: /Acter le résultat/ })).not.toBeInTheDocument()
  })

  it('rend un barrage PÉRIMÉ sans formulaire de saisie ni « Acter »', () => {
    // Le second bloquant : le groupe a changé, le verdict sera écarté — laisser saisir et acter
    // faisait tirer un groupe incomplet pour rien, en répondant 200.
    afficher([barrage({ perime: true, est_resolu: false, groupes_a_rejouer: [[1, 2]] })])

    expect(screen.getByRole('alert')).toHaveTextContent(/ne porte plus sur les archers/)
    expect(screen.queryByRole('button', { name: /Enregistrer la manche/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Acter le résultat/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Annuler ce barrage/ })).toBeInTheDocument()
  })

  it('signale un barrage INCOHÉRENT sans faire disparaître le panneau', () => {
    afficher([barrage({ incoherent: true, est_resolu: false, groupes_a_rejouer: [[1, 2]] })])

    expect(screen.getByText(/Saisie incohérente/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Annuler ce barrage/ })).toBeInTheDocument()
  })

  it('propose « Faire tirer » sur une égalité signalée', () => {
    afficher([], [{ rang: 2, archer_ids: [1, 2] }])

    expect(screen.getByRole('button', { name: /Faire tirer/ })).toBeInTheDocument()
    expect(screen.getByText(/MARTIN Alice, DURAND Chloé/)).toBeInTheDocument()
  })

  it('ne masque pas « Faire tirer » à cause d’un barrage périmé au même rang', () => {
    // Le barrage ouvert ne porte plus sur le bon groupe : il ne doit pas empêcher d'en relancer un.
    afficher(
      [barrage({ perime: true, participants: [1, 2] })],
      [{ rang: 2, archer_ids: [1, 2, 3] }],
    )

    expect(screen.getByRole('button', { name: /Faire tirer/ })).toBeInTheDocument()
  })

  it('masque « Faire tirer » quand le barrage ouvert porte bien sur le groupe signalé', () => {
    afficher(
      [barrage({ est_resolu: false, groupes_a_rejouer: [[1, 2]] })],
      [{ rang: 2, archer_ids: [1, 2] }],
    )

    expect(screen.queryByRole('button', { name: /Faire tirer/ })).not.toBeInTheDocument()
  })
})
