// Tests de l'ordre et du filtrage de la liste des tournois (retour maquettes du 04/08/2026).
//
// Les cas dérivent des **phrases du commanditaire**, citées dans `tri.ts`, et non de la lecture de
// l'implémentation : c'est la règle 9 du projet. Chaque test nomme la phrase qu'il garde.

import { describe, expect, it } from 'vitest'
import type { StatutTournoi, Tournoi } from '../competition/api'
import {
  dateDuJour,
  estAujourdhui,
  filtrerParStatut,
  ordonnerTournois,
  statutsPresents,
} from './tri'

function tournoi(id: number, statut: StatutTournoi, date: string): Tournoi {
  return {
    id,
    nom: `T${id}`,
    date,
    lieu: null,
    type_tournoi: 'non_officiel',
    statut,
  }
}

describe('ordonnerTournois', () => {
  it('« statut (1. en cours, 2. prêt à lancer, 3. terminer, 4. brouillon) puis par date »', () => {
    const liste = [
      tournoi(1, 'brouillon', '2026-09-01'),
      tournoi(2, 'termine', '2026-06-01'),
      tournoi(3, 'pret', '2026-08-05'),
      tournoi(4, 'en_cours', '2026-08-05'),
    ]
    expect(ordonnerTournois(liste).map((t) => t.id)).toEqual([4, 3, 2, 1])
  })

  it('« en pause » reste collé à « en cours » : c’est le tournoi du jour, seulement suspendu', () => {
    const liste = [tournoi(1, 'pret', '2026-08-05'), tournoi(2, 'en_pause', '2026-08-05')]
    expect(ordonnerTournois(liste).map((t) => t.id)).toEqual([2, 1])
  })

  it('« d’abord les tournois prêts, surtout si on est à la date prévue » : le plus proche en tête', () => {
    const liste = [
      tournoi(1, 'pret', '2026-11-20'),
      tournoi(2, 'pret', '2026-08-05'), // aujourd'hui
      tournoi(3, 'pret', '2026-09-12'),
    ]
    expect(ordonnerTournois(liste).map((t) => t.id)).toEqual([2, 3, 1])
  })

  it('les tournois clos se lisent du plus récent au plus ancien', () => {
    // On ne cherche jamais « le tournoi d'il y a trois ans » en premier.
    const liste = [
      tournoi(1, 'termine', '2024-02-01'),
      tournoi(2, 'termine', '2026-06-01'),
      tournoi(3, 'termine', '2025-03-01'),
    ]
    expect(ordonnerTournois(liste).map((t) => t.id)).toEqual([2, 3, 1])
  })

  it('archivé et annulé ferment la marche : il n’y a plus rien à y faire', () => {
    const liste = [
      tournoi(1, 'annule', '2026-08-05'),
      tournoi(2, 'archive', '2026-08-05'),
      tournoi(3, 'brouillon', '2026-08-05'),
    ]
    expect(ordonnerTournois(liste).map((t) => t.id)).toEqual([3, 2, 1])
  })

  it('ne réordonne pas la liste reçue (le cache est partagé avec les autres écrans)', () => {
    const liste = [tournoi(1, 'brouillon', '2026-09-01'), tournoi(2, 'en_cours', '2026-08-05')]
    ordonnerTournois(liste)
    expect(liste.map((t) => t.id)).toEqual([1, 2])
  })
})

describe('dateDuJour', () => {
  it('donne la date **locale**, pas la date UTC', () => {
    // 23 h 30 le 5 août en heure locale : `toISOString()` aurait rendu le 5 ou le 6 selon le fuseau.
    // La construction locale garantit qu'on lit bien « aujourd'hui » tel que l'organisateur le vit.
    const soir = new Date(2026, 7, 5, 23, 30)
    expect(dateDuJour(soir)).toBe('2026-08-05')
  })

  it('complète le mois et le jour sur deux chiffres', () => {
    expect(dateDuJour(new Date(2026, 0, 9))).toBe('2026-01-09')
  })
})

describe('estAujourdhui', () => {
  it('repère le tournoi du jour', () => {
    expect(estAujourdhui(tournoi(1, 'pret', '2026-08-05'), '2026-08-05')).toBe(true)
    expect(estAujourdhui(tournoi(1, 'pret', '2026-08-06'), '2026-08-05')).toBe(false)
  })
})

describe('filtre par statut', () => {
  const liste = [
    tournoi(1, 'en_cours', '2026-08-05'),
    tournoi(2, 'pret', '2026-08-06'),
    tournoi(3, 'pret', '2026-08-07'),
    tournoi(4, 'brouillon', '2026-09-01'),
  ]

  it('ne propose que des états présents, avec leur décompte, dans l’ordre d’affichage', () => {
    expect(statutsPresents(liste)).toEqual([
      { statut: 'en_cours', nombre: 1 },
      { statut: 'pret', nombre: 2 },
      { statut: 'brouillon', nombre: 1 },
    ])
  })

  it('un filtre vide vaut « tout » — jamais une liste vide inexpliquée', () => {
    expect(filtrerParStatut(liste, new Set())).toHaveLength(4)
  })

  it('retient les états cochés', () => {
    const retenus = new Set<StatutTournoi>(['pret'])
    expect(filtrerParStatut(liste, retenus).map((t) => t.id)).toEqual([2, 3])
  })
})
