import { describe, expect, it } from 'vitest'

import type { Bloc, Flux } from './modele'
import {
  COULOIR_SAUT,
  ESPACE_COLONNE,
  HAUTEUR_TOUR,
  LARGEUR_BLOC,
  disposer,
  hauteurBloc,
} from './geometrie'

function flux(ordre_source: number, ordre_cible: number, effectif: number | null = 8): Flux {
  return {
    ordre_source,
    ordre_cible,
    nature: 'rangs',
    effectif,
    rang_debut: 1,
    rang_fin: effectif,
    tour: null,
    issue: null,
  }
}

function bloc(ordre: number, entrees: Flux[] = [], tours = 0): Bloc {
  return {
    ordre,
    type: 'elimination_directe',
    effectif: 8,
    tranche: [1, 8],
    nb_volees: null,
    nb_fleches_par_volee: null,
    tours: Array.from({ length: tours }, (_, index) => ({
      tour: index + 1,
      duels: 1,
      plage_gagnants: [1, 1] as [number, number],
      plage_perdants: [2, 2] as [number, number],
    })),
    entrees,
    sorties: [],
    sans_suite: 0,
    anomalies: [],
  }
}

describe('hauteurBloc', () => {
  it('grandit d’une ligne par braquet affiché', () => {
    expect(hauteurBloc(bloc(1, [], 3)) - hauteurBloc(bloc(1, [], 0))).toBe(3 * HAUTEUR_TOUR)
  })
})

describe('disposer', () => {
  it('indexe les nœuds par position, pas par ordre', () => {
    // Deux étapes de même ordre : brouillon licite (anomalie bloquante, mais enregistrable). Une
    // clé de rendu fondée sur `ordre` ferait collision et masquerait un bloc.
    const plan = disposer([bloc(1), bloc(1)])

    expect(plan.noeuds.map((n) => n.index)).toEqual([0, 1])
  })

  it('rend un plan vide pour aucun bloc', () => {
    const plan = disposer([])

    expect(plan.noeuds).toEqual([])
    expect(plan.aretes).toEqual([])
    expect(plan.largeur).toBe(0)
  })

  it('place une colonne par phase, dans l’ordre, de gauche à droite', () => {
    const plan = disposer([bloc(3), bloc(1), bloc(2)])

    expect(plan.noeuds.map((n) => n.ordre)).toEqual([1, 2, 3])
    const [premier, second] = plan.noeuds
    expect(second!.x - premier!.x).toBe(LARGEUR_BLOC + ESPACE_COLONNE)
  })

  it('aligne les blocs en haut, quelles que soient leurs hauteurs', () => {
    const plan = disposer([bloc(1, [], 0), bloc(2, [flux(1, 2)], 5)])

    expect(new Set(plan.noeuds.map((n) => n.y)).size).toBe(1)
  })

  it('trace une flèche par prélèvement, du bord droit de la source au bord gauche de la cible', () => {
    const plan = disposer([bloc(1), bloc(2, [flux(1, 2)])])

    expect(plan.aretes).toHaveLength(1)
    const arete = plan.aretes[0]!
    const [source, cible] = plan.noeuds
    expect(arete.trace.startsWith(`M ${source!.x + LARGEUR_BLOC} `)).toBe(true)
    expect(arete.trace).toContain(`L ${cible!.x} `)
    expect(arete.saute).toBe(false)
  })

  it('renvoie sous les blocs une flèche qui saute une colonne', () => {
    // « Les gagnants de la phase 1 rejoignent la phase 3 » : en ligne droite, la flèche
    // traverserait le bloc 2.
    const plan = disposer([bloc(1), bloc(2), bloc(3, [flux(1, 3)])])

    const arete = plan.aretes[0]!
    expect(arete.saute).toBe(true)
    expect(arete.trace).toContain('Q')
  })

  it('réserve le couloir du bas seulement quand une flèche y passe', () => {
    const sansSaut = disposer([bloc(1), bloc(2, [flux(1, 2)])])
    const avecSaut = disposer([bloc(1), bloc(2), bloc(3, [flux(1, 3)])])

    expect(avecSaut.hauteur - sansSaut.hauteur).toBe(COULOIR_SAUT)
  })

  it('étage les prélèvements multiples d’un même bloc pour qu’ils ne se superposent pas', () => {
    const plan = disposer([bloc(1), bloc(2), bloc(3, [flux(1, 3), flux(2, 3)])])

    const [premiere, seconde] = plan.aretes
    expect(premiere!.etiquette_y).not.toBe(seconde!.etiquette_y)
  })

  it('donne des clés distinctes à deux prélèvements de la même paire de phases', () => {
    const plan = disposer([bloc(1), bloc(2, [flux(1, 2, 4), flux(1, 2, 8)])])

    expect(new Set(plan.aretes.map((a) => a.cle)).size).toBe(2)
  })

  it('ne dessine aucune flèche pour une source absente du plan', () => {
    // Format incohérent (source introuvable) : le diagnostic le signale déjà comme bloquant, le
    // dessin ne doit pas inventer une flèche qui ne mène nulle part.
    const plan = disposer([bloc(2, [flux(1, 2)])])

    expect(plan.aretes).toEqual([])
  })

  it('pose l’étiquette d’une flèche courbe sur la courbe, pas au creux', () => {
    const plan = disposer([bloc(1), bloc(2), bloc(3, [flux(1, 3)])])

    const arete = plan.aretes[0]!
    const creux = Number(arete.trace.split('Q ')[1]!.split(' ')[1])
    expect(arete.etiquette_y).toBeLessThan(creux)
  })
})
