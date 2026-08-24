// Tests de la présentation de la mixité de club (E03US006, RG-3) — logique pure, en node (comme
// `planConsultation.test.ts`). On couvre le décompte des cibles signalées et le résumé chiffré
// affiché en bannière (accord singulier/pluriel, `null` quand tout est mixé).

import { describe, expect, it } from 'vitest'
import type { CiblePlacee } from './api'
import type { ReferentielsDuPlan } from './presentation'
import {
  LIBELLE_CLOISONNEMENT,
  compterMixiteNonGarantie,
  lignesDeReperes,
  reperesArcher,
  resumeCloisonnementNonRespecte,
  resumeMixiteNonGarantie,
} from './presentation'

function cible(over: Partial<CiblePlacee> = {}): CiblePlacee {
  return {
    index: 1,
    capacite: 4,
    placements: [],
    mixite_non_garantie: false,
    cloisonnement_non_respecte: false,
    ...over,
  }
}

describe('compterMixiteNonGarantie', () => {
  it('compte les cibles signalées, ignore les autres', () => {
    const cibles = [
      cible(),
      cible({ index: 2, mixite_non_garantie: true }),
      cible({ index: 3, mixite_non_garantie: true }),
    ]
    expect(compterMixiteNonGarantie(cibles)).toBe(2)
  })

  it('vaut 0 quand aucune cible n’est signalée', () => {
    expect(compterMixiteNonGarantie([cible(), cible({ index: 2 })])).toBe(0)
  })
})

describe('resumeMixiteNonGarantie', () => {
  it('renvoie null quand la mixité est garantie partout (pas de bannière)', () => {
    expect(resumeMixiteNonGarantie([cible(), cible({ index: 2 })])).toBeNull()
  })

  it('accorde au singulier pour une seule cible', () => {
    const resume = resumeMixiteNonGarantie([cible({ mixite_non_garantie: true })])
    expect(resume).toContain('1 cible sans')
    expect(resume).not.toContain('cibles')
  })

  it('accorde au pluriel pour plusieurs cibles', () => {
    const resume = resumeMixiteNonGarantie([
      cible({ mixite_non_garantie: true }),
      cible({ index: 2, mixite_non_garantie: true }),
    ])
    expect(resume).toContain('2 cibles sans')
  })
})

// --- Cloisonnement des cibles (E03US007) --------------------------------------------------------

describe('resumeCloisonnementNonRespecte', () => {
  it('renvoie null quand aucune cible ne viole le réglage (pas de bannière)', () => {
    expect(resumeCloisonnementNonRespecte([cible(), cible({ index: 2 })])).toBeNull()
  })

  it('accorde au singulier et dit quoi faire', () => {
    const resume = resumeCloisonnementNonRespecte([cible({ cloisonnement_non_respecte: true })])
    expect(resume).toContain('1 cible ne respecte pas')
    // Un signal qui n'indique pas le geste correctif est un reproche sans issue : la bannière ne
    // peut apparaître que sur un plan antérieur au réglage, la régénération est la sortie.
    expect(resume).toContain('régénérez')
  })

  it('accorde au pluriel', () => {
    const resume = resumeCloisonnementNonRespecte([
      cible({ cloisonnement_non_respecte: true }),
      cible({ index: 2, cloisonnement_non_respecte: true }),
    ])
    expect(resume).toContain('2 cibles ne respectent pas')
  })
})

describe('LIBELLE_CLOISONNEMENT', () => {
  it('couvre les quatre positions du réglage', () => {
    expect(Object.keys(LIBELLE_CLOISONNEMENT)).toEqual([
      'aucun',
      'categorie',
      'blason',
      'blason_et_categorie',
    ])
  })
})

// --- Repères d'un archer sur son jeton (E16US005) ------------------------------------------------
//
// Ce que ces tests gardent : les repères servent à **expliquer les badges** de la cible (mixité,
// cloisonnement). Un repère faux ou bouche-trou serait pire que pas de repère du tout — l'organisateur
// déplacerait un archer sur une information inventée.

const REFERENTIELS: ReferentielsDuPlan = {
  clubs: new Map([[7, 'Arc Club de Kervignarc']]),
  categories: new Map([[3, 'Senior 1 Femme']]),
  blasons: new Map([[9, 'Triple 40']]),
}

describe('reperesArcher', () => {
  it('CA — porte le club, la catégorie et le blason, dans cet ordre', () => {
    // L'ordre n'est pas cosmétique : il va du plus large (le club, RG-3) au plus fin (le blason,
    // RG-4), donc dans le sens où l'organisateur lit un conflit de cloisonnement.
    expect(reperesArcher({ club_id: 7, categorie_id: 3 }, 9, REFERENTIELS)).toEqual([
      'Arc Club de Kervignarc',
      'Senior 1 Femme',
      'Triple 40',
    ])
  })

  it('un club non renseigné se dit « club inconnu », jamais « aucun club » (ADR-0014)', () => {
    // C'est **la cause** du badge « mixité non garantie » que le serveur pose sur la cible : la
    // taire laisserait l'organisateur devant un reproche sans explication.
    expect(reperesArcher({ club_id: null, categorie_id: 3 }, 9, REFERENTIELS)).toEqual([
      'club inconnu',
      'Senior 1 Femme',
      'Triple 40',
    ])
  })

  it('un identifiant introuvable est omis, jamais rendu en « #7 »', () => {
    // Cas réel du premier rendu : les trois référentiels arrivent **après** le plan. Afficher
    // « Club #7 » puis le vrai nom ferait clignoter quarante lignes ; l'omission ne coûte rien.
    const vide: ReferentielsDuPlan = { clubs: new Map(), categories: new Map(), blasons: new Map() }
    expect(reperesArcher({ club_id: 7, categorie_id: 3 }, 9, vide)).toEqual([])
  })

  it('sans archer connu, aucun repère — le nom seul suffit', () => {
    expect(reperesArcher(undefined, 9, REFERENTIELS)).toEqual([])
  })

  it('sans blason (un archer en réserve), les deux autres repères tiennent', () => {
    // La réserve ne porte pas de blason : `Conflit` n'a que l'archer et la raison. Les repères y
    // restent utiles — « sans blason » + la catégorie dit **quelle** catégorie n'a pas de carton.
    expect(reperesArcher({ club_id: 7, categorie_id: 3 }, null, REFERENTIELS)).toEqual([
      'Arc Club de Kervignarc',
      'Senior 1 Femme',
    ])
  })
})

describe('lignesDeReperes', () => {
  it('sépare le club — insécable, donc tronqué — de ce qui explique le cloisonnement', () => {
    // La séparation n'est pas cosmétique : la ligne du club porte une ellipse, l'autre non, parce
    // que le blason est le seul repère qui explique le cloisonnement sous les réglages `blason` et
    // `blason_et_categorie` — et il est en fin de chaîne, donc le premier effacé par une troncature.
    expect(lignesDeReperes({ club_id: 7, categorie_id: 3 }, 9, REFERENTIELS)).toEqual({
      club: 'Arc Club de Kervignarc',
      cloisonnement: ['Senior 1 Femme', 'Triple 40'],
    })
  })

  it('⚠️ le club manquant ne fait PAS remonter la catégorie sur sa ligne', () => {
    // **Le cas qui a motivé cette fonction.** `useClubs`, `useCategories` et `useBlasons` sont trois
    // requêtes distinctes : si celle des clubs arrive en retard ou échoue seule, une liste plate
    // commence par la catégorie, et un découpage `reperes[0]` l'affichait comme s'il s'agissait du
    // club. Ici la ligne du club est simplement absente.
    const sansClubs: ReferentielsDuPlan = { ...REFERENTIELS, clubs: new Map() }
    expect(lignesDeReperes({ club_id: 7, categorie_id: 3 }, 9, sansClubs)).toEqual({
      club: null,
      cloisonnement: ['Senior 1 Femme', 'Triple 40'],
    })
  })

  it('un club non renseigné occupe bien sa ligne (ADR-0014)', () => {
    expect(lignesDeReperes({ club_id: null, categorie_id: 3 }, 9, REFERENTIELS).club).toBe(
      'club inconnu',
    )
  })

  it('sans archer connu, aucune ligne', () => {
    expect(lignesDeReperes(undefined, 9, REFERENTIELS)).toEqual({ club: null, cloisonnement: [] })
  })
})
