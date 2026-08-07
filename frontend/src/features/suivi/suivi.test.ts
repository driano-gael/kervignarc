// Tests de la logique pure de « suivi » (E07US006), dérivés du CA : « recherche par nom » et « une
// carte par archer avec cible/position ». En node, sans composant.

import { describe, expect, it } from 'vitest'
import type { Archer } from '../competition/api'
import type { Depart } from '../departs/api'
import type { PlanDeCibles } from '../placement/api'
import { construireJournee, filtrerArchers, placeDansPlan, rechercherArchers } from './suivi'

const archer = (id: number, nom: string, prenom: string): Archer => ({
  id,
  tournoi_id: 1,
  nom,
  prenom,
  categorie_id: 1,
  cible: null,
  club_id: null,
  handicap_officiel: null,
  handicap_surcharge: null,
  handicap: 0,
})

const depart = (id: number, numero: number, horaire: string): Depart => ({
  id,
  tournoi_id: 1,
  numero,
  horaire,
  tarif_centimes: 0,
  quota: null,
  etat: 'ouvert',
})

const planAvec = (
  departId: number,
  placements: { index: number; position: string; archerId: number }[],
): PlanDeCibles => ({
  depart_id: departId,
  cibles: placements.map((p) => ({
    index: p.index,
    capacite: 4,
    mixite_non_garantie: false,
    cloisonnement_non_respecte: false,
    placements: [{ position: p.position, archer_id: p.archerId, blason_id: 1, inscription_id: 1 }],
  })),
  conflits: [],
})

describe('filtrerArchers — recherche par nom', () => {
  const archers = [
    archer(1, 'Martin', 'Paul'),
    archer(2, 'Durand', 'Rémy'),
    archer(3, 'Martinez', 'Sophie'),
  ]

  it('une requête vide ne propose rien (la recherche est l’exception, pas la porte)', () => {
    expect(filtrerArchers(archers, '')).toEqual([])
    expect(filtrerArchers(archers, '   ')).toEqual([])
  })

  it('matche sur le nom, insensible à la casse', () => {
    expect(filtrerArchers(archers, 'mart').map((a) => a.id)).toEqual([1, 3])
  })

  it('matche aussi sur le prénom', () => {
    expect(filtrerArchers(archers, 'sophie').map((a) => a.id)).toEqual([3])
  })

  it('matche sur une sous-chaîne au milieu du nom (pas seulement le préfixe)', () => {
    expect(filtrerArchers(archers, 'arti').map((a) => a.id)).toEqual([1, 3])
  })

  it('tolère les accents (« remy » retrouve « Rémy »)', () => {
    expect(filtrerArchers(archers, 'remy').map((a) => a.id)).toEqual([2])
  })

  it('sans correspondance, renvoie une liste vide', () => {
    expect(filtrerArchers(archers, 'zzz')).toEqual([])
  })
})

// E16US004, **dérivé du CA** « recherche : filtre par club, liste qui se met à jour à la frappe,
// état de suivi actionnable sur chaque ligne » (questionnaire P01 : *« mettre un filtre de tri par
// club en plus dans la recherche ; une liste d'archers se met à jour à mesure de la recherche »*).
// Écrit avant le câblage de l'écran (règle 9). Seuls les deux premiers volets sont de la logique
// pure ; l'« état actionnable » est du rendu, vérifié à la recette.
describe('rechercherArchers — nom et club', () => {
  const archers = [
    { ...archer(1, 'Martin', 'Paul'), club_id: 7 },
    { ...archer(2, 'Durand', 'Rémy'), club_id: 8 },
    { ...archer(3, 'Martinez', 'Sophie'), club_id: 7 },
    // Club encore **inconnu** (ADR-0014) : `null` n'est jamais « aucun club ».
    { ...archer(4, 'Marty', 'Jean'), club_id: null },
  ]

  it('sans nom ni club, ne propose rien', () => {
    // On garde la règle d'E07US006 (D-09 : la recherche est l'exception, pas la porte) : sans aucun
    // critère, on ne déverse pas l'annuaire.
    expect(rechercherArchers(archers, { requete: '', clubId: null })).toEqual([])
  })

  it('un club seul suffit à lister ses archers, sans rien taper', () => {
    // C'est le « filtre en plus » demandé : on choisit un club et la liste apparaît — sinon le
    // filtre ne servirait qu'à réduire une recherche déjà faite, ce qui n'est pas ce qui est
    // demandé (« un filtre de tri par club **en plus** »).
    expect(rechercherArchers(archers, { requete: '', clubId: 7 }).map((a) => a.id)).toEqual([1, 3])
  })

  it('nom et club se cumulent', () => {
    expect(rechercherArchers(archers, { requete: 'martin', clubId: 7 }).map((a) => a.id)).toEqual([
      1, 3,
    ])
    expect(rechercherArchers(archers, { requete: 'martin', clubId: 8 })).toEqual([])
  })

  it('le nom seul ignore le club (comportement d’avant, inchangé)', () => {
    expect(rechercherArchers(archers, { requete: 'mart', clubId: null }).map((a) => a.id)).toEqual([
      1, 3, 4,
    ])
  })

  it('un archer au club inconnu ne tombe dans aucun club', () => {
    // Le piège d'ADR-0014 : `club_id === null` veut dire « pas encore renseigné ». Le ranger
    // d'office dans le club filtré ferait croire qu'il en est, et l'y chercher ensuite en vain.
    expect(rechercherArchers(archers, { requete: 'marty', clubId: 7 })).toEqual([])
    expect(rechercherArchers(archers, { requete: '', clubId: 7 }).map((a) => a.id)).toEqual([1, 3])
  })
})

describe('placeDansPlan — place d’un archer sur un départ', () => {
  const plan: PlanDeCibles = {
    depart_id: 10,
    cibles: [
      {
        index: 1,
        capacite: 4,
        mixite_non_garantie: false,
        cloisonnement_non_respecte: false,
        placements: [{ position: 'A', archer_id: 1, blason_id: 1, inscription_id: 100 }],
      },
      {
        index: 2,
        capacite: 4,
        mixite_non_garantie: false,
        cloisonnement_non_respecte: false,
        placements: [{ position: 'C', archer_id: 2, blason_id: 1, inscription_id: 101 }],
      },
    ],
    conflits: [],
  }

  it('archer posé → sa cible et sa position', () => {
    expect(placeDansPlan(plan, 2)).toEqual({ cible: 2, position: 'C' })
  })

  it('archer absent du plan (en réserve) → null', () => {
    expect(placeDansPlan(plan, 3)).toBeNull()
  })

  it('plan sans cible → null', () => {
    expect(placeDansPlan({ depart_id: 10, cibles: [], conflits: [] }, 1)).toBeNull()
  })
})

describe('construireJournee — la journée d’un archer (départs + plans, pas les inscriptions)', () => {
  const departs = [depart(10, 1, '09:00'), depart(20, 2, '14:00')]

  it('archer posé sur un départ → une ligne créneau + place', () => {
    const plans = new Map([[10, planAvec(10, [{ index: 3, position: 'B', archerId: 7 }])]])

    expect(construireJournee(7, departs, plans)).toEqual([
      { departId: 10, numeroDepart: 1, horaire: '09:00', cible: 3, position: 'B' },
    ])
  })

  it('archer posé sur deux départs → deux lignes triées par numéro de départ', () => {
    // Départs passés **dans le désordre** (n° 2 avant n° 1) pour que le test exerce vraiment le tri :
    // retirer le `.sort()` de `construireJournee` doit le faire échouer (retour de revue B1).
    const departsDesordre = [depart(20, 2, '14:00'), depart(10, 1, '09:00')]
    const plans = new Map([
      [20, planAvec(20, [{ index: 5, position: 'A', archerId: 7 }])],
      [10, planAvec(10, [{ index: 3, position: 'B', archerId: 7 }])],
    ])

    expect(construireJournee(7, departsDesordre, plans).map((l) => l.numeroDepart)).toEqual([1, 2])
  })

  it('archer posé sur aucun plan → journée vide', () => {
    const plans = new Map([[10, planAvec(10, [{ index: 3, position: 'B', archerId: 99 }])]])

    expect(construireJournee(7, departs, plans)).toEqual([])
  })

  it('départ dont le plan n’est pas (encore) chargé → départ ignoré, pas de crash', () => {
    // Seul le plan du départ 10 est présent dans la Map ; le départ 20 est sauté.
    const plans = new Map([[10, planAvec(10, [{ index: 3, position: 'B', archerId: 7 }])]])

    expect(construireJournee(7, departs, plans).map((l) => l.departId)).toEqual([10])
  })
})
