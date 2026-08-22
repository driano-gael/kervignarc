import { describe, expect, it } from 'vitest'

import type { Etape, Source } from '../patrimoine/api'
import {
  ajouterEtape,
  decrireEtape,
  decrireSource,
  deplacerEtape,
  lireEntier,
  remplacerEtape,
  retirerEtape,
} from './sequence'

function rangs(ordre_source: number, rang_debut = 1, rang_fin: number | null = 8): Source {
  return { ordre_source, nature: 'rangs', rang_debut, rang_fin, tour: null, issue: null }
}

function etape(ordre: number, sources: Source[] = []): Etape {
  return {
    ordre,
    type: 'elimination_directe',
    bareme: null,
    validation: null,
    poules: null,
    big_shoot_off: null,
    suisse: null,
    colline: null,
    decoupage: null,
    sources,
    effectif: null,
    profondeur: null,
    // E05US033 : les deux réglages neufs, au défaut d'avant l'US.
    arrets: [],
  }
}

describe('renumérotation et remappage des prélèvements', () => {
  it('renumérote les ordres selon la position', () => {
    const suite = deplacerEtape([etape(1), etape(2), etape(3)], 2, 0)

    expect(suite.map((e) => e.ordre)).toEqual([1, 2, 3])
  })

  it('fait suivre un prélèvement la phase qu’il désignait', () => {
    // C prélève dans B (ordre 2). On remonte B en tête : C doit prélever dans B, devenue 1ʳᵉ.
    const avant = [etape(1), etape(2), etape(3, [rangs(2)])]

    const apres = deplacerEtape(avant, 1, 0)

    expect(apres[2]!.sources[0]!.ordre_source).toBe(1)
  })

  it('ne laisse jamais une phase se prélever elle-même après un déplacement', () => {
    // Le cas le plus visible : descendre la qualification sous le tableau qui s’y alimente.
    const avant = [etape(1), etape(2, [rangs(1)])]

    const apres = deplacerEtape(avant, 0, 1)

    expect(apres[0]!.sources[0]!.ordre_source).not.toBe(apres[0]!.ordre)
    expect(apres[0]!.sources[0]!.ordre_source).toBe(2)
  })

  it('remappe aussi après un retrait', () => {
    const avant = [etape(1), etape(2), etape(3, [rangs(3 - 1)])]

    const apres = retirerEtape(avant, 0)

    expect(apres.map((e) => e.ordre)).toEqual([1, 2])
    expect(apres[1]!.sources[0]!.ordre_source).toBe(1)
  })

  it('rend introuvable — et non voisin — un prélèvement dont la phase a disparu', () => {
    // ⚠️ Le test qui occupait cette place prenait deux étapes, le seul cas où le défaut se voyait
    // par auto-référence. Avec une étape **survivante après** celle qu’on retire, la valeur
    // conservée retombait silencieusement sur elle : la finale puisait dans le mauvais tableau,
    // cible existante et antérieure, donc aucune anomalie.
    const avant = [etape(1), etape(2, [rangs(1)]), etape(3, [rangs(1)]), etape(4, [rangs(2)])]

    const apres = retirerEtape(avant, 1)

    expect(apres.map((e) => e.ordre)).toEqual([1, 2, 3])
    // L’ancienne phase 3 est devenue la 2 : le prélèvement qui visait la 1 la suit correctement.
    expect(apres[1]!.sources[0]!.ordre_source).toBe(1)
    // Celui qui visait la phase retirée ne doit **pas** avoir glissé sur elle.
    expect(apres[2]!.sources[0]!.ordre_source).not.toBe(2)
    // Il désigne un ordre hors séquence : le diagnostic rendra `source_phase_introuvable`.
    expect(apres[2]!.sources[0]!.ordre_source).toBeGreaterThan(apres.length)
  })

  it('rend introuvable le prélèvement quand il ne reste plus rien avant', () => {
    const apres = retirerEtape([etape(1), etape(2, [rangs(1)])], 0)

    expect(apres).toHaveLength(1)
    expect(apres[0]!.ordre).toBe(1)
    expect(apres[0]!.sources[0]!.ordre_source).toBeGreaterThan(1)
  })

  it('ajoute en fin de séquence sans toucher aux prélèvements existants', () => {
    const suite = ajouterEtape([etape(1), etape(2, [rangs(1)])], etape(99, [rangs(2)]))

    expect(suite.map((e) => e.ordre)).toEqual([1, 2, 3])
    expect(suite[1]!.sources[0]!.ordre_source).toBe(1)
    expect(suite[2]!.sources[0]!.ordre_source).toBe(2)
  })

  it('remplace une étape en place', () => {
    const suite = remplacerEtape([etape(1), etape(2)], 1, { ...etape(2), effectif: 16 })

    expect(suite[1]!.effectif).toBe(16)
    expect(suite.map((e) => e.ordre)).toEqual([1, 2])
  })
})

describe('decrireSource', () => {
  it('décrit une plage fermée', () => {
    expect(decrireSource(rangs(1, 1, 32))).toBe('rangs 1 à 32 de la phase 1')
  })

  it('décrit une plage ouverte', () => {
    expect(decrireSource(rangs(1, 33, null))).toBe('rangs 33 et suivants de la phase 1')
  })

  it('décrit une issue de tour', () => {
    const source: Source = {
      ordre_source: 2,
      nature: 'issue_de_tour',
      rang_debut: 1,
      rang_fin: null,
      tour: 3,
      issue: 'perdants',
    }

    expect(decrireSource(source)).toBe('perdants du tour 3 de la phase 2')
  })

  it('décrit « le reste »', () => {
    const source: Source = {
      ordre_source: 1,
      nature: 'reste',
      rang_debut: 1,
      rang_fin: null,
      tour: null,
      issue: null,
    }

    expect(decrireSource(source)).toBe('le reste de la phase 1')
  })
})

describe('decrireEtape', () => {
  it('dit « tous les inscrits » quand la phase ne prélève nulle part', () => {
    expect(decrireEtape(etape(1))).toBe('tous les inscrits')
  })

  it('joint barème, effectif et prélèvements', () => {
    const qualif: Etape = {
      ordre: 2,
      type: 'elimination_directe',
      bareme: { nb_volees: 20, nb_fleches_par_volee: 3 },
      validation: null,
      sources: [rangs(1, 1, 32)],
      profondeur: null,
      poules: null,
      big_shoot_off: null,
      suisse: null,
      colline: null,
      decoupage: null,
      // E05US033 : les deux réglages neufs, au défaut d'avant l'US.
      arrets: [],
      effectif: 32,
    }

    expect(decrireEtape(qualif)).toBe('20×3 · 32 archers · rangs 1 à 32 de la phase 1')
  })
})

describe('lireEntier', () => {
  it('distingue « non renseigné » de « invalide »', () => {
    // `Number('')` vaut 0 et `Number('abc')` vaut NaN, sérialisé `null` : sans cette distinction,
    // une faute de frappe effaçait silencieusement l’effectif déclaré.
    expect(lireEntier('')).toBeNull()
    expect(lireEntier('   ')).toBeNull()
    expect(lireEntier('abc')).toBeUndefined()
    expect(lireEntier('0')).toBeUndefined()
    expect(lireEntier('-3')).toBeUndefined()
    expect(lireEntier('2.5')).toBeUndefined()
    expect(lireEntier('20')).toBe(20)
  })
})
