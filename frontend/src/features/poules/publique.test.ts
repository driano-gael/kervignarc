// Tests de l'adaptation publique des **poules** (E05US031).
//
// Deux règles s'y jouent, et aucune des deux ne se lit dans le code de la vue :
//
//  1. **le regroupement par tour** — un round-robin se lit tour par tour, et le serveur rend ses
//     rencontres à plat, avec un `tour` ; les grouper est donc une décision, pas un détail ;
//  2. **l'ordre des cinq critères de départage** (§10.1) — c'est lui qui rend le classement
//     *traçable* : deux archers à égalité de points doivent pouvoir se lire de gauche à droite
//     jusqu'à ce qui les a séparés.

import { describe, expect, it } from 'vitest'
import type { EtatPoules, PoulePublique, RencontrePublique } from './api'
import { formatPublicDesPoules } from './publique'

const MARTIN = { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' }
const DURAND = { archer_id: 2, nom: 'DURAND', prenom: 'Eve' }

function mkRencontre(over: Partial<RencontrePublique> = {}): RencontrePublique {
  return {
    numero: 1,
    poule: 1,
    tour: 1,
    couloirs: null,
    haut: MARTIN,
    bas: DURAND,
    points_haut: null,
    points_bas: null,
    vainqueur: null,
    termine: false,
    validee: false,
    desynchronisee: false,
    ...over,
  }
}

function mkPoule(over: Partial<PoulePublique> = {}): PoulePublique {
  return {
    numero: 1,
    membres: [MARTIN, DURAND],
    bloc: [
      [1, 'A'],
      [1, 'B'],
    ],
    rencontres: [mkRencontre()],
    classement: [],
    qualifies: [],
    barrage_requis: false,
    ...over,
  }
}

function mkEtat(over: Partial<EtatPoules> = {}): EtatPoules {
  return {
    phase_id: 4,
    repartition: { effectif: 2, taille_visee: 2, nb_poules: 1, tailles: [2] },
    poules: [mkPoule()],
    conflits: [],
    ...over,
  }
}

describe('formatPublicDesPoules', () => {
  it('groupe les rencontres par tour, dans l’ordre', () => {
    const format = formatPublicDesPoules(
      mkEtat({
        poules: [
          mkPoule({
            rencontres: [
              mkRencontre({ numero: 3, tour: 2 }),
              mkRencontre({ numero: 1, tour: 1 }),
              mkRencontre({ numero: 2, tour: 1 }),
            ],
          }),
        ],
      }),
    )

    const tours = format.blocs[0]?.tours ?? []
    expect(tours.map((t) => t.libelle)).toEqual(['Tour 1', 'Tour 2'])
    expect(tours[0]?.rencontres.map((r) => r.numero)).toEqual([1, 2])
  })

  it('ne clôt un tour que si toutes ses rencontres sont validées', () => {
    const format = formatPublicDesPoules(
      mkEtat({
        poules: [
          mkPoule({
            rencontres: [
              mkRencontre({ numero: 1, validee: true }),
              // Tirée mais pas scellée : le tour n'est pas clos pour autant.
              mkRencontre({ numero: 2, termine: true, validee: false }),
            ],
          }),
        ],
      }),
    )

    expect(format.blocs[0]?.tours[0]?.clos).toBe(false)
  })

  it('range les cinq critères de départage dans l’ordre du §10.1', () => {
    const format = formatPublicDesPoules(
      mkEtat({
        poules: [
          mkPoule({
            classement: [
              {
                rang: 1,
                archer_id: MARTIN.archer_id,
                points_match: 4,
                diff_sets: 3,
                diff_score: 12,
                nb_dix: 5,
                nb_neuf: 2,
                ex_aequo: false,
              },
            ],
          }),
        ],
      }),
    )

    expect(format.blocs[0]?.colonnes.map((c) => c.libelle)).toEqual([
      'Pts',
      'Δ sets',
      'Δ score',
      '10',
      '9',
    ])
    expect(format.blocs[0]?.classement[0]).toEqual({
      rang: 1,
      archer_id: 1,
      nom: 'Luc MARTIN',
      valeurs: ['4', '3', '12', '5', '2'],
      ex_aequo: false,
    })
  })

  it('annonce un barrage requis et un plan non posé', () => {
    // Rapporté, jamais tu (ADR-0024). Sans la première ligne, deux archers au même rang se lisent
    // comme un bug d'affichage ; sans la seconde, l'absence de cible se lit comme une donnée perdue.
    const format = formatPublicDesPoules(
      mkEtat({ poules: [mkPoule({ bloc: null, barrage_requis: true })] }),
    )

    expect(format.blocs[0]?.notes).toHaveLength(2)
    expect(format.blocs[0]?.notes[0]).toContain('plan de cibles')
    expect(format.blocs[0]?.notes[1]).toContain('barrage')
  })

  // ⚠️ **La fixture porte la vraie valeur d'enum du serveur, pas une phrase inventée.** La première
  // rédaction posait `raison: 'aucun bloc libre de 6 couloirs'` — un DTO que le serveur n'émet
  // jamais : `ConflitReponse.raison` vaut `RaisonConflitBloc.value`, donc `salle_pleine`,
  // `non_posee` ou `sans_rencontre`. Le test décrivait un contrat imaginé, et laissait passer
  // l'affichage du code brut au public.
  it('nomme la poule que le plan n’a pas pu placer, en français', () => {
    const format = formatPublicDesPoules(
      mkEtat({ conflits: [{ poule: 3, raison: 'salle_pleine' }] }),
    )

    expect(format.conflits).toEqual([
      'Poule 3 — Pas assez de couloirs libres dans la salle : les cibles ne sont pas attribuées.',
    ])
  })

  it('ne montre jamais un code technique au spectateur', () => {
    const format = formatPublicDesPoules(
      mkEtat({
        conflits: [
          { poule: 1, raison: 'non_posee' },
          { poule: 2, raison: 'sans_rencontre' },
          // Un code qu'un serveur plus récent nommerait : le repli reste une phrase.
          { poule: 3, raison: 'raison_inconnue_du_bundle' },
        ],
      }),
    )

    for (const conflit of format.conflits) {
      expect(conflit).not.toMatch(/_/)
    }
  })

  it('ordonne les poules par numéro, quel que soit l’ordre du serveur', () => {
    const format = formatPublicDesPoules(
      mkEtat({ poules: [mkPoule({ numero: 2 }), mkPoule({ numero: 1 })] }),
    )

    expect(format.blocs.map((b) => b.titre)).toEqual(['Poule 1', 'Poule 2'])
  })
})
