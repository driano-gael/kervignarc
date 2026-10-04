// Tests de la logique pure de la saisie en duels (E04US013) — libellés, avancement, statut, injection
// optimiste. Le serveur reste l'autorité (résultat, mode, zones) ; on teste ce qui pilote l'affichage.

import { describe, expect, it } from 'vitest'
import type { Duel, Phase, Resultat, SaisirBarrage, SaisirManche } from './api'
import {
  archersARouter,
  baremeDeManche,
  campApresFleche,
  duellistesDuForfait,
  estOuvrable,
  etatBarrage,
  etatManche,
  flechesApresZone,
  grouperParTour,
  injecterBarrage,
  injecterManche,
  libelleMode,
  libelleTour,
  mancheExistante,
  pastillesManches,
  retenirPhase,
  phasesDeTableau,
  pointsZone,
  mancheNeuveFermee,
  prochaineMancheASaisir,
  saisieVerrouillee,
  signatureBarrage,
  signatureManche,
  statutDuel,
  totalVolee,
} from './duel'

function duel(over: Partial<Duel> = {}): Duel {
  return {
    numero: 1,
    tour: 1,
    place_en_jeu: null,
    haut: { archer_id: 1, nom: 'DUPONT', prenom: 'Jean' },
    bas: { archer_id: 2, nom: 'MARTIN', prenom: 'Luc' },
    est_bye: false,
    mode: 'sets',
    nb_manches: 5,
    nb_fleches_par_volee: 3,
    points_pour_gagner: 6,
    nb_fleches_barrage: 1,
    zones: ['10', '9', '8', '7', '6', 'M'],
    validee_par: null,
    manches: [],
    barrage: null,
    resultat: null,
    ...over,
  }
}

describe('libelleMode', () => {
  it('distingue sets, cumul (poulies) et absence de mode', () => {
    expect(libelleMode('sets')).toBe('Système de sets')
    expect(libelleMode('cumul')).toBe('Cumul (arc à poulies)')
    expect(libelleMode(null)).toBe('')
  })
})

describe('libelleTour', () => {
  it('nomme le tour par distance à la finale', () => {
    expect(libelleTour({ tour: 2, place_en_jeu: [1, 2] }, 2)).toBe('Finale')
    expect(libelleTour({ tour: 1, place_en_jeu: null }, 2)).toBe('Demi-finales')
    expect(libelleTour({ tour: 1, place_en_jeu: null }, 3)).toBe('Quarts de finale')
    expect(libelleTour({ tour: 1, place_en_jeu: null }, 4)).toBe('1/8 de finale')
  })

  it('distingue la petite finale (3ᵉ place) de la finale, même tour', () => {
    expect(libelleTour({ tour: 2, place_en_jeu: [3, 4] }, 2)).toBe('Petite finale (3ᵉ place)')
  })
})

describe('grouperParTour', () => {
  // Un match minimal pour les regroupements (seuls tour/place/numero comptent ici).
  const match = (numero: number, tour: number, place: number[] | null): Duel =>
    duel({ numero, tour, place_en_jeu: place })

  it('range finale puis petite finale (même dernier tour) sous des sections distinctes', () => {
    const nbTours = 2
    const duels = [
      match(1, 2, [1, 2]), // finale
      match(2, 2, [3, 4]), // petite finale (même tour que la finale)
      match(3, 1, null), // demie
      match(4, 1, null), // demie
    ]
    const groupes = grouperParTour(duels, nbTours)
    expect(groupes.map((g) => g.titre)).toEqual([
      'Finale',
      'Petite finale (3ᵉ place)',
      'Demi-finales',
    ])
    // Les deux demies fusionnent en une seule section.
    expect(groupes[2]?.duels.map((d) => d.numero)).toEqual([3, 4])
  })

  it('un tableau à deux archers n’a qu’une finale', () => {
    const groupes = grouperParTour([match(1, 1, [1, 2])], 1)
    expect(groupes.map((g) => g.titre)).toEqual(['Finale'])
  })

  it('ordonne les tours du plus proche de la finale au plus lointain', () => {
    const groupes = grouperParTour([match(1, 1, null), match(2, 3, [1, 2]), match(3, 2, null)], 3)
    expect(groupes.map((g) => g.titre)).toEqual(['Finale', 'Demi-finales', 'Quarts de finale'])
  })
})

describe('prochaineMancheASaisir', () => {
  it('la plus petite manche non encore saisie', () => {
    expect(prochaineMancheASaisir({ manches: [], resultat: null }, 5)).toBe(1)
    expect(
      prochaineMancheASaisir({ manches: [{ numero: 1, haut: [], bas: [] }], resultat: null }, 5),
    ).toBe(2)
  })

  it('reste sur la dernière si toutes sont saisies', () => {
    const manches = [1, 2, 3, 4, 5].map((numero) => ({ numero, haut: [], bas: [] }))
    expect(prochaineMancheASaisir({ manches, resultat: null }, 5)).toBe(5)
  })

  // E01US011 : à 4-4 au format club, le barrage est requis — pas une 5ᵉ manche.
  const quatreManches = [1, 2, 3, 4].map((numero) => ({ numero, haut: [], bas: [] }))
  const resultat = { points_haut: 4, points_bas: 4, vainqueur: null }

  it('à égalité en attente de barrage, ne propose pas de manche neuve', () => {
    const duel = {
      manches: quatreManches,
      resultat: { ...resultat, termine: false, barrage_requis: true },
    }
    expect(mancheNeuveFermee(duel)).toBe(true)
    expect(prochaineMancheASaisir(duel, 5)).toBe(4)
  })

  it('un duel tranché avant la dernière manche ne propose pas de manche neuve', () => {
    const duel = {
      manches: quatreManches.slice(0, 2),
      resultat: { ...resultat, termine: true, barrage_requis: false },
    }
    expect(prochaineMancheASaisir(duel, 5)).toBe(2)
  })

  it('un duel en cours propose la manche suivante', () => {
    const duel = {
      manches: quatreManches.slice(0, 2),
      resultat: { ...resultat, termine: false, barrage_requis: false },
    }
    expect(mancheNeuveFermee(duel)).toBe(false)
    expect(prochaineMancheASaisir(duel, 5)).toBe(3)
  })
})

describe('mancheExistante', () => {
  it('retrouve une manche par numéro, ou null', () => {
    const d = duel({ manches: [{ numero: 2, haut: ['10'], bas: ['9'] }] })
    expect(mancheExistante(d, 2)?.haut).toEqual(['10'])
    expect(mancheExistante(d, 1)).toBeNull()
  })
})

describe('statutDuel', () => {
  it('bye', () => {
    expect(statutDuel(duel({ est_bye: true }))).toBe('bye')
  })
  it('adversaires inconnus', () => {
    expect(statutDuel(duel({ bas: null }))).toBe('attente_adversaires')
  })
  it('à saisir (aucun tir)', () => {
    expect(statutDuel(duel())).toBe('a_saisir')
  })
  it('en cours (des manches, pas encore tranché)', () => {
    const d = duel({
      manches: [{ numero: 1, haut: ['10'], bas: ['9'] }],
      resultat: {
        points_haut: 2,
        points_bas: 0,
        vainqueur: null,
        termine: false,
        barrage_requis: false,
      },
    })
    expect(statutDuel(d)).toBe('en_cours')
  })
  it('à valider (tranché, non validé)', () => {
    const d = duel({
      resultat: {
        points_haut: 6,
        points_bas: 0,
        vainqueur: 'haut',
        termine: true,
        barrage_requis: false,
      },
    })
    expect(statutDuel(d)).toBe('a_valider')
  })
  it('validé', () => {
    expect(statutDuel(duel({ validee_par: 'ROUX' }))).toBe('valide')
  })
})

describe('injecterManche (optimiste hors-ligne)', () => {
  const corps: SaisirManche = {
    tournoi_id: 1,
    phase_id: 2,
    match_numero: 1,
    numero: 1,
    valeurs_haut: ['10', '10', '10'],
    valeurs_bas: ['9', '9', '9'],
    identifiant_saisie: 'id-1',
  }

  it('ajoute la manche et marque le duel en attente', () => {
    const d = injecterManche(duel(), corps)
    expect(d.manches).toHaveLength(1)
    expect(d.manches[0]).toEqual({ numero: 1, haut: ['10', '10', '10'], bas: ['9', '9', '9'] })
    expect(d.en_attente).toBe(true)
  })

  it('remplace une manche de même numéro (réédition) et ne recompute pas le résultat', () => {
    const base = duel({
      manches: [{ numero: 1, haut: ['6', '6', '6'], bas: ['10', '10', '10'] }],
      resultat: {
        points_haut: 0,
        points_bas: 2,
        vainqueur: null,
        termine: false,
        barrage_requis: false,
      },
    })
    const d = injecterManche(base, corps)
    expect(d.manches).toHaveLength(1)
    expect(d.manches[0]?.haut).toEqual(['10', '10', '10'])
    expect(d.resultat?.points_bas).toBe(2) // résultat inchangé : autorité serveur (ADR-0049)
  })
})

describe('injecterBarrage (optimiste hors-ligne)', () => {
  it('pose le barrage et marque le duel en attente', () => {
    const corps: SaisirBarrage = {
      tournoi_id: 1,
      phase_id: 2,
      match_numero: 1,
      fleches_haut: ['10', '9', '9'],
      fleches_bas: ['9', '9', '9'],
      gagnant_designe: null,
      identifiant_saisie: 'id-b',
    }
    const d = injecterBarrage(duel(), corps)
    expect(d.barrage).toEqual({
      haut: ['10', '9', '9'],
      bas: ['9', '9', '9'],
      gagnant_designe: null,
    })
    expect(d.en_attente).toBe(true)
  })
})

describe('totalVolee', () => {
  it('somme les zones, M = 0', () => {
    expect(totalVolee(['10', '9', 'M'])).toBe(19)
    expect(totalVolee([])).toBe(0)
  })
})

// ⚠️ `DETTE-111` — **moitié front du cliquet** : `duel.ts` réécrit encore la règle zone → points du
// domaine, que la saisie de qualification lit désormais servie. L'autre moitié fige la même liste
// côté serveur (`test_domain_blason.py`). Recréée ici en revue d'E17US011 (axes B, D) : elle avait
// disparu avec l'ancien `pointsZone` de `volees.ts`, laissant le jumeau sans garde.
describe('pointsZone (duel) — le miroir du domaine', () => {
  it('donne à chaque zone du vocabulaire FFTA sa valeur, M valant 0', () => {
    const zones = ['10', '9', '8', '7', '6', '5', '4', '3', '2', '1', 'M']
    expect(zones.map(pointsZone)).toEqual([10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0])
  })
})

// --- Décisions de l'écran sorties du composant (E00US024) : l'oracle est le comportement d'avant. ---

function resultat(over: Partial<Resultat> = {}): Resultat {
  return {
    points_haut: 0,
    points_bas: 0,
    vainqueur: null,
    termine: false,
    barrage_requis: false,
    ...over,
  }
}

const EQUIPE = { archer_id: null, nom: 'Les Flèches', prenom: '', membres: ['A', 'B'] }

describe('estOuvrable', () => {
  it('ferme le bye et le duel sans adversaires, ouvre tout le reste', () => {
    expect(estOuvrable('bye')).toBe(false)
    expect(estOuvrable('attente_adversaires')).toBe(false)
    for (const statut of ['a_saisir', 'en_cours', 'a_valider', 'valide'] as const) {
      expect(estOuvrable(statut)).toBe(true)
    }
  })
})

describe('phasesDeTableau', () => {
  it('ne garde que les phases à élimination directe, dans leur ordre', () => {
    const phases: Phase[] = [
      { id: 1, ordre: 1, type: 'qualification' },
      { id: 2, ordre: 2, type: 'elimination_directe' },
      { id: 3, ordre: 3, type: 'poules' },
      { id: 4, ordre: 4, type: 'elimination_directe' },
    ]
    expect(phasesDeTableau(phases).map((p) => p.id)).toEqual([2, 4])
  })

  it('rend une liste vide sans phase de tableau', () => {
    expect(phasesDeTableau([])).toEqual([])
    expect(phasesDeTableau([{ id: 1, ordre: 1, type: 'qualification' }])).toEqual([])
  })
})

describe('retenirPhase', () => {
  const tableaux: Phase[] = [
    { id: 2, ordre: 2, type: 'elimination_directe' },
    { id: 4, ordre: 4, type: 'elimination_directe' },
  ]

  it('garde la phase choisie si elle appartient à la liste', () => {
    expect(retenirPhase(4, tableaux)).toBe(4)
  })

  it('oublie une phase étrangère à la liste (changement de créneau)', () => {
    expect(retenirPhase(7, tableaux)).toBeNull()
    expect(retenirPhase(2, [])).toBeNull()
  })

  it('reste sans phase quand aucune n’est choisie', () => {
    expect(retenirPhase(null, tableaux)).toBeNull()
  })
})

describe('saisieVerrouillee', () => {
  it('verrouille un duel validé par le serveur', () => {
    expect(saisieVerrouillee(duel({ validee_par: 'Scoreur 1' }))).toBe(true)
  })

  it('verrouille localement une validation en file hors-ligne', () => {
    expect(saisieVerrouillee(duel({ validation_en_attente: true }))).toBe(true)
  })

  it('laisse ouverte une saisie ni validée ni en file', () => {
    expect(saisieVerrouillee(duel())).toBe(false)
    expect(saisieVerrouillee(duel({ validation_en_attente: false }))).toBe(false)
  })
})

describe('duellistesDuForfait', () => {
  it('propose les deux archers d’un duel de tableau ouvert', () => {
    expect(duellistesDuForfait(duel(), 'tableau')).toEqual({ hautId: 1, basId: 2 })
  })

  it('ne propose rien en poule', () => {
    expect(duellistesDuForfait(duel(), 'poule')).toBeNull()
  })

  it('ne propose rien sur une saisie close', () => {
    expect(duellistesDuForfait(duel({ validee_par: 'Scoreur 1' }), 'tableau')).toBeNull()
    expect(duellistesDuForfait(duel({ validation_en_attente: true }), 'tableau')).toBeNull()
  })

  it('ne propose rien quand un camp est une équipe ou inconnu', () => {
    expect(duellistesDuForfait(duel({ haut: EQUIPE }), 'tableau')).toBeNull()
    expect(duellistesDuForfait(duel({ bas: EQUIPE }), 'tableau')).toBeNull()
    expect(duellistesDuForfait(duel({ bas: null }), 'tableau')).toBeNull()
  })

  it('accepte l’identifiant 0 (seul `null` écarte un camp)', () => {
    const haut = { archer_id: 0, nom: 'ZERO', prenom: 'Z' }
    expect(duellistesDuForfait(duel({ haut }), 'tableau')).toEqual({ hautId: 0, basId: 2 })
  })
})

describe('archersARouter', () => {
  it('rend les deux archers quand la validation est partie', () => {
    expect(archersARouter(duel(), {})).toEqual([1, 2])
    expect(archersARouter(duel(), { validation_en_attente: false })).toEqual([1, 2])
  })

  it('ne route personne sur une validation mise en file hors-ligne', () => {
    expect(archersARouter(duel(), { validation_en_attente: true })).toEqual([])
  })

  it('écarte les camps sans archer (équipe, camp inconnu)', () => {
    expect(archersARouter(duel({ haut: EQUIPE }), {})).toEqual([2])
    expect(archersARouter(duel({ haut: EQUIPE, bas: null }), {})).toEqual([])
  })
})

describe('pastillesManches', () => {
  it('une pastille par manche : saisie, active, ouverte', () => {
    const d = duel({ manches: [{ numero: 1, haut: ['10'], bas: ['9'] }] })
    expect(pastillesManches(d, 3, 2)).toEqual([
      {
        numero: 1,
        saisie: true,
        fermee: false,
        active: false,
        classes: 'saisie__nav-volee saisie__nav-volee--saisie',
      },
      {
        numero: 2,
        saisie: false,
        fermee: false,
        active: true,
        classes: 'saisie__nav-volee saisie__nav-volee--actif',
      },
      { numero: 3, saisie: false, fermee: false, active: false, classes: 'saisie__nav-volee' },
    ])
  })

  it('ferme les manches non saisies d’un duel tranché, pas les saisies', () => {
    const d = duel({
      manches: [{ numero: 1, haut: ['10'], bas: ['9'] }],
      resultat: resultat({ termine: true }),
    })
    expect(pastillesManches(d, 2, 1).map((p) => p.fermee)).toEqual([false, true])
  })

  it('ferme aussi en attente de barrage', () => {
    const d = duel({ resultat: resultat({ barrage_requis: true }) })
    expect(pastillesManches(d, 2, 1).map((p) => p.fermee)).toEqual([true, true])
  })

  it('aucune pastille pour un barème sans manche', () => {
    expect(pastillesManches(duel(), 0, 1)).toEqual([])
  })
})

describe('baremeDeManche', () => {
  it('lit le barème que porte le duel', () => {
    expect(baremeDeManche(duel({ nb_manches: 5, nb_fleches_par_volee: 2 }))).toEqual({
      nbManches: 5,
      nbFleches: 2,
    })
  })

  it('retombe sur une manche de trois flèches quand le duel ne porte pas de barème', () => {
    expect(baremeDeManche(duel({ nb_manches: null, nb_fleches_par_volee: null }))).toEqual({
      nbManches: 1,
      nbFleches: 3,
    })
  })
})

describe('etatManche', () => {
  const base = { bufferHaut: [], bufferBas: [], campActif: 'haut' as const, nbFleches: 3 }

  it('manche vide : on frappe, rien à effacer ni à enregistrer', () => {
    expect(etatManche({ ...base, envoiEnCours: false })).toEqual({
      campComplet: false,
      zonesActives: true,
      effacable: false,
      enregistrable: false,
    })
  })

  it('camp actif plein, l’autre vide : zones fermées, rien d’enregistrable', () => {
    const etat = etatManche({ ...base, bufferHaut: ['10', '9', '8'], envoiEnCours: false })
    expect(etat).toMatchObject({ campComplet: true, zonesActives: false, enregistrable: false })
    expect(etat.effacable).toBe(true)
  })

  it('l’état suit le camp actif, pas le premier camp', () => {
    const etat = etatManche({
      ...base,
      bufferHaut: ['10', '9', '8'],
      campActif: 'bas',
      envoiEnCours: false,
    })
    expect(etat).toMatchObject({ campComplet: false, zonesActives: true, effacable: false })
  })

  it('deux camps complets : enregistrable', () => {
    const etat = etatManche({
      ...base,
      bufferHaut: ['10', '9', '8'],
      bufferBas: ['7', '6', 'M'],
      envoiEnCours: false,
    })
    expect(etat.enregistrable).toBe(true)
  })

  it('un envoi en cours fige tout, même deux camps complets', () => {
    const etat = etatManche({
      ...base,
      bufferHaut: ['10', '9', '8'],
      bufferBas: ['7', '6', 'M'],
      envoiEnCours: true,
    })
    expect(etat).toEqual({
      campComplet: true,
      zonesActives: false,
      effacable: false,
      enregistrable: false,
    })
  })

  it('le compte est « au moins » nbFleches, pas « exactement »', () => {
    const etat = etatManche({
      ...base,
      bufferHaut: ['10', '9', '8', '7'],
      bufferBas: ['7', '6', 'M'],
      envoiEnCours: false,
    })
    expect(etat).toMatchObject({ campComplet: true, enregistrable: true })
  })
})

describe('campApresFleche', () => {
  it('reste sur le camp tant qu’il n’est pas rempli', () => {
    expect(campApresFleche('haut', 2, 0, 3)).toBe('haut')
  })

  it('bascule sur l’autre camp dès le camp rempli, s’il reste à saisir', () => {
    expect(campApresFleche('haut', 3, 0, 3)).toBe('bas')
    expect(campApresFleche('bas', 3, 2, 3)).toBe('haut')
  })

  it('ne bascule pas quand l’autre camp est déjà complet', () => {
    expect(campApresFleche('haut', 3, 3, 3)).toBe('haut')
    expect(campApresFleche('bas', 3, 4, 3)).toBe('bas')
  })
})

describe('signatureManche', () => {
  it('encode le numéro et les deux volées persistées', () => {
    expect(signatureManche(2, { numero: 2, haut: ['10', '9'], bas: ['M'] })).toBe('2:10,9:M')
  })

  it('une manche absente ne signe que son numéro', () => {
    expect(signatureManche(3, null)).toBe('3::')
  })

  it('change dès que le numéro ou le contenu persisté change', () => {
    const base = signatureManche(1, { numero: 1, haut: ['10'], bas: ['9'] })
    expect(signatureManche(2, { numero: 1, haut: ['10'], bas: ['9'] })).not.toBe(base)
    expect(signatureManche(1, { numero: 1, haut: ['10'], bas: ['8'] })).not.toBe(base)
    expect(signatureManche(1, { numero: 1, haut: ['10'], bas: ['9'] })).toBe(base)
  })
})

describe('signatureBarrage', () => {
  it('encode les flèches et la désignation', () => {
    expect(signatureBarrage({ haut: ['10'], bas: ['10'], gagnant_designe: 'bas' })).toBe(
      '10:10:bas',
    )
    expect(signatureBarrage({ haut: ['9', '8'], bas: ['X'], gagnant_designe: null })).toBe('9,8:X:')
  })

  it('un barrage absent a une empreinte vide stable', () => {
    expect(signatureBarrage(null)).toBe('::')
  })

  it('change quand seule la désignation change', () => {
    const sans = signatureBarrage({ haut: ['10'], bas: ['10'], gagnant_designe: null })
    const avec = signatureBarrage({ haut: ['10'], bas: ['10'], gagnant_designe: 'haut' })
    expect(avec).not.toBe(sans)
  })
})

describe('etatBarrage', () => {
  it('incomplet : rien n’est prêt ni à égalité', () => {
    expect(etatBarrage(['10'], [], null, 1)).toEqual({
      complets: false,
      egales: false,
      pretAEnvoyer: false,
    })
  })

  it('complet et inégal : prêt sans désignation', () => {
    expect(etatBarrage(['10'], ['9'], null, 1)).toEqual({
      complets: true,
      egales: false,
      pretAEnvoyer: true,
    })
  })

  it('complet et à égalité : prêt seulement une fois le gagnant désigné', () => {
    expect(etatBarrage(['10'], ['10'], null, 1).pretAEnvoyer).toBe(false)
    expect(etatBarrage(['10'], ['10'], 'bas', 1)).toEqual({
      complets: true,
      egales: true,
      pretAEnvoyer: true,
    })
  })

  it('compare les totaux à plusieurs flèches (équipe), M valant 0', () => {
    expect(etatBarrage(['10', '8'], ['9', '9'], null, 2).egales).toBe(true)
    expect(etatBarrage(['10', 'M'], ['9', '1'], null, 2).egales).toBe(true)
    expect(etatBarrage(['10', '9'], ['9', '9'], null, 2).egales).toBe(false)
  })

  it('exige le compte exact de flèches, pas un minimum', () => {
    expect(etatBarrage(['10', '9'], ['10'], null, 1).complets).toBe(false)
  })
})

describe('flechesApresZone', () => {
  it('à une flèche, la zone touchée remplace la précédente', () => {
    expect(flechesApresZone(['9'], '10', 1)).toEqual(['10'])
    expect(flechesApresZone([], '10', 1)).toEqual(['10'])
  })

  it('à plusieurs flèches, la zone touchée s’ajoute', () => {
    expect(flechesApresZone(['9'], '10', 3)).toEqual(['9', '10'])
  })
})
