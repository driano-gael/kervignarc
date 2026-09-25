// Tests de la mise en forme du plan de cibles pour la consultation publique (E07US001). Logique
// pure, testée en node — calqué sur `supervision/etat.test.ts`. On vérifie la jointure nom, les deux
// tris (cibles par index, places par position) et le repli quand un archer manque de l'annuaire.

import { describe, expect, it } from 'vitest'
import type { PlanDeCibles } from './api'
import { construirePlanConsultation, mesPlaces } from './planConsultation'

// Fabrique minimale d'un plan : seuls `index`, `capacite` et les placements (position + archer)
// comptent ici ; `blason_id`/`inscription_id` sont du remplissage sans effet sur la mise en forme.
function plan(
  cibles: { index: number; capacite: number; places: { position: string; archer_id: number }[] }[],
): PlanDeCibles {
  return {
    depart_id: 1,
    conflits: [],
    cibles: cibles.map((c) => ({
      index: c.index,
      capacite: c.capacite,
      mixite_non_garantie: false,
      cloisonnement_non_respecte: false,
      placements: c.places.map((p) => ({
        position: p.position,
        archer_id: p.archer_id,
        blason_id: 1,
        inscription_id: p.archer_id * 10,
      })),
    })),
  }
}

describe('construirePlanConsultation', () => {
  it('résout le nom de chaque archer depuis l’annuaire', () => {
    const noms = new Map([
      [1, 'Marie Dupont'],
      [2, 'Jean Martin'],
    ])
    const resultat = construirePlanConsultation(
      plan([{ index: 1, capacite: 4, places: [{ position: 'A', archer_id: 1 }] }]),
      noms,
    )
    expect(resultat).toEqual([{ index: 1, places: [{ position: 'A', nom: 'Marie Dupont' }] }])
  })

  it('trie les cibles par index (ordre de la salle), pas l’ordre reçu', () => {
    const resultat = construirePlanConsultation(
      plan([
        { index: 3, capacite: 4, places: [] },
        { index: 1, capacite: 4, places: [] },
        { index: 2, capacite: 4, places: [] },
      ]),
      new Map(),
    )
    expect(resultat.map((c) => c.index)).toEqual([1, 2, 3])
  })

  it('trie les places par position (A avant B) quelle que soit leur arrivée', () => {
    const noms = new Map([
      [1, 'Alice'],
      [2, 'Bob'],
      [3, 'Chloé'],
    ])
    const resultat = construirePlanConsultation(
      plan([
        {
          index: 1,
          capacite: 4,
          places: [
            { position: 'C', archer_id: 3 },
            { position: 'A', archer_id: 1 },
            { position: 'B', archer_id: 2 },
          ],
        },
      ]),
      noms,
    )
    expect(resultat[0]!.places.map((p) => p.position)).toEqual(['A', 'B', 'C'])
    expect(resultat[0]!.places.map((p) => p.nom)).toEqual(['Alice', 'Bob', 'Chloé'])
  })

  it('archer absent de l’annuaire → libellé de repli, jamais une ligne muette', () => {
    const resultat = construirePlanConsultation(
      plan([{ index: 1, capacite: 4, places: [{ position: 'A', archer_id: 42 }] }]),
      new Map(),
    )
    expect(resultat[0]!.places[0]!.nom).toBe('Archer #42')
  })

  it('cible sans archer posé → cible présente, liste de places vide', () => {
    const resultat = construirePlanConsultation(
      plan([{ index: 5, capacite: 3, places: [] }]),
      new Map(),
    )
    expect(resultat).toEqual([{ index: 5, places: [] }])
  })
})

// P04, variante retenue au questionnaire du 04/08 : « Ma cible d'abord, plan ensuite » (✅ validé
// tel quel). Le spectateur qui suit des archers lit **leurs** places avant la grille. E17US009.
describe('mesPlaces', () => {
  const noms = new Map([
    [7, 'Paul MARTIN'],
    [8, 'Jean DURAND'],
    [9, 'Luc MARTINEAU'],
  ])
  const salle = plan([
    { index: 3, capacite: 4, places: [{ position: 'A', archer_id: 8 }] },
    {
      index: 12,
      capacite: 4,
      places: [
        { position: 'B', archer_id: 7 },
        { position: 'A', archer_id: 9 },
      ],
    },
  ])

  it('rend la cible et le couloir de chaque archer suivi posé sur ce départ', () => {
    expect(mesPlaces(salle, [7], noms)).toEqual([
      { archerId: 7, nom: 'Paul MARTIN', cible: 12, position: 'B' },
    ])
  })

  it('suit l’ordre de la salle (cible, puis couloir), pas l’ordre des suivis', () => {
    expect(mesPlaces(salle, [7, 8, 9], noms).map((p) => p.archerId)).toEqual([8, 9, 7])
  })

  it('ignore un archer suivi qui ne tire pas sur ce départ', () => {
    expect(mesPlaces(salle, [7, 404], noms).map((p) => p.archerId)).toEqual([7])
  })

  it('ne rend rien quand on ne suit personne — le plan reste seul à l’écran', () => {
    expect(mesPlaces(salle, [], noms)).toEqual([])
  })

  it('archer absent de l’annuaire → même repli que la grille', () => {
    expect(mesPlaces(salle, [7], new Map())[0]?.nom).toBe('Archer #7')
  })
})
