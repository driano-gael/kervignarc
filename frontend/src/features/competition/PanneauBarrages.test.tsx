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
import userEvent from '@testing-library/user-event'
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

  it('propose « Faire tirer » quand le seul barrage au même rang est ACTÉ et SAIN', () => {
    // Un barrage acté dont le verdict tient ne bloque rien : il n'y aurait d'ailleurs pas
    // d'égalité signalée à son rang si son verdict s'appliquait — ce cas n'existe que le temps
    // qu'une nouvelle égalité s'y forme.
    afficher([barrage({ clos: true, participants: [1, 2] })], [{ rang: 2, archer_ids: [1, 2] }])

    expect(screen.getByRole('button', { name: /Faire tirer/ })).toBeInTheDocument()
  })

  it('masque « Faire tirer » au-dessus d’un barrage acté mais PÉRIMÉ', () => {
    // ⚠️ Le bloquant : l'alerte rouge dit « annulez-le puis relancez », et le bouton était offert
    // juste au-dessus — le serveur acceptait, produisant deux cartes « acté » au même rang aux
    // verdicts inversés, sans le moindre signal.
    afficher(
      [barrage({ clos: true, perime: true, participants: [1, 2] })],
      [{ rang: 2, archer_ids: [1, 2, 3] }],
    )

    expect(screen.queryByRole('button', { name: /Faire tirer/ })).not.toBeInTheDocument()
  })

  it('masque « Faire tirer » au-dessus d’un barrage encore OUVERT, mêmes tireurs ou non', () => {
    afficher(
      [barrage({ est_resolu: false, groupes_a_rejouer: [[1, 2]], participants: [1, 2] })],
      [{ rang: 2, archer_ids: [1, 2, 3] }],
    )

    expect(screen.queryByRole('button', { name: /Faire tirer/ })).not.toBeInTheDocument()
  })

  it('ne masque pas « Faire tirer » à cause d’un barrage d’un AUTRE rang', () => {
    afficher(
      [barrage({ rang_dispute: 5, est_resolu: false, groupes_a_rejouer: [[1, 2]] })],
      [{ rang: 2, archer_ids: [1, 2] }],
    )

    expect(screen.getByRole('button', { name: /Faire tirer/ })).toBeInTheDocument()
  })

  it('ne masque pas « Faire tirer » à cause d’un barrage de POULE au même rang', () => {
    // La régression que le commentaire du prédicat nomme, et que rien n'épinglait.
    afficher(
      [barrage({ portee: 'poule', est_resolu: false, groupes_a_rejouer: [[1, 2]] })],
      [{ rang: 2, archer_ids: [1, 2] }],
    )

    expect(screen.getByRole('button', { name: /Faire tirer/ })).toBeInTheDocument()
  })

  // ⚠️ Ces deux cas **interrogeaient `window.confirm`** jusqu'au 04/08/2026. La confirmation passe
  // désormais par un vrai dialogue (A15), donc l'oracle change de support — mais **pas de contenu** :
  // ce qu'ils garantissent reste exactement la même règle métier, à savoir que la perte des rangs
  // n'est annoncée que lorsqu'elle est vraie. On lit maintenant le texte affiché plutôt que
  // l'argument d'une boîte native, ce qui est en prime plus proche de ce que l'organisateur voit.
  it('annonce la perte des rangs quand on annule un barrage ACTÉ et sain', async () => {
    // Annuler un barrage acté **remet les archers à égalité**, ce que « N manche(s) seront
    // effacées » ne dit pas. Sur un barrage périmé, en revanche, les rangs sont **déjà** repartagés
    // — la promesse serait fausse, d'où la condition `clos && !perime`.
    afficher([barrage({ clos: true })])

    await userEvent.click(screen.getByRole('button', { name: /Annuler ce barrage/ }))

    expect(screen.getByRole('dialog')).toHaveTextContent('repartageront leur rang')
  })

  it('ne promet pas la perte des rangs sur un barrage PÉRIMÉ (ils sont déjà repartagés)', async () => {
    afficher([barrage({ clos: true, perime: true })])

    await userEvent.click(screen.getByRole('button', { name: /Annuler ce barrage/ }))

    expect(screen.getByRole('dialog')).not.toHaveTextContent('repartageront')
  })

  it('allume l’ambre sur une égalité signalée, même sans aucun barrage', () => {
    // Quatrième branche de `aFaire`, sans quoi son retrait passait inaperçu : c'est pourtant le cas
    // le plus courant — une place à départager, rien encore d'ouvert.
    const { container } = afficher([], [{ rang: 2, archer_ids: [1, 2] }])
    expect(container.querySelector('.carte--barrages-actif')).not.toBeNull()
  })

  it('allume l’ambre sur un barrage ACTÉ mais PÉRIMÉ', () => {
    // ⚠️ Le cas que le correctif du barrage clos vient d'ouvrir : le seul barrage acté qui doit
    // rallumer l'alerte. Vérifié par mutation — sans ce cas, retirer `|| b.perime` de `aFaire`
    // laissait la suite verte, `!b.clos` masquant tous les autres cas périmés.
    const { container } = afficher([barrage({ clos: true, perime: true })])
    expect(container.querySelector('.carte--barrages-actif')).not.toBeNull()
  })

  it('allume l’ambre sur un barrage ACTÉ mais INCOHÉRENT', () => {
    const { container } = afficher([barrage({ clos: true, incoherent: true })])
    expect(container.querySelector('.carte--barrages-actif')).not.toBeNull()
  })

  it('allume l’ambre tant qu’un barrage reste à tirer', () => {
    const { container } = afficher([barrage({ est_resolu: false, groupes_a_rejouer: [[1, 2]] })])
    expect(container.querySelector('.carte--barrages-actif')).not.toBeNull()
  })
})
