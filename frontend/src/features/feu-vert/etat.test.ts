import { describe, expect, it } from 'vitest'
import type { DuelAVenir, ResumeLancement } from './api'
import {
  actionDuel,
  afficheDuel,
  archersForfaitables,
  libelleBouton,
  libelleCibles,
  nomDuelliste,
} from './etat'

function duel(patch: Partial<DuelAVenir>): DuelAVenir {
  return {
    numero: 1,
    tour: 1,
    haut: { archer_id: 1, nom: 'Hood', prenom: 'Robin' },
    bas: { archer_id: 2, nom: 'Scarlet', prenom: 'Will' },
    participants_connus: true,
    cible_haut: 4,
    cible_bas: 4,
    cible_attribuee: true,
    sources_en_attente: [],
    pret_a_lancer: true,
    blocage: null,
    ...patch,
  }
}

describe('afficheDuel', () => {
  it('marque un duel prêt en vert', () => {
    expect(afficheDuel(duel({ pret_a_lancer: true }))).toEqual({ classe: 'pret', libelle: 'Prêt' })
  })

  it('nomme le blocage d’un duel en attente (jamais un simple drapeau)', () => {
    const bloque = duel({ pret_a_lancer: false, blocage: 'en attente du duel n°2' })
    expect(afficheDuel(bloque)).toEqual({ classe: 'attente', libelle: 'en attente du duel n°2' })
  })

  it('retombe sur un libellé générique si le blocage n’est pas renseigné', () => {
    expect(afficheDuel(duel({ pret_a_lancer: false, blocage: null }))).toEqual({
      classe: 'attente',
      libelle: 'En attente',
    })
  })
})

describe('nomDuelliste', () => {
  it('rend prénom + nom', () => {
    expect(nomDuelliste({ archer_id: 1, nom: 'Hood', prenom: 'Robin' })).toBe('Robin Hood')
  })

  it('rend « — » pour un camp sans occupant', () => {
    expect(nomDuelliste(null)).toBe('—')
  })
})

describe('libelleCibles', () => {
  it('rend une cible unique quand les deux duellistes la partagent', () => {
    expect(libelleCibles(duel({ cible_haut: 4, cible_bas: 4 }))).toBe('cible 4')
  })

  it('rend les deux cibles distinctes, triées', () => {
    expect(libelleCibles(duel({ cible_haut: 7, cible_bas: 4 }))).toBe('cibles 4 et 7')
  })

  it('rend une chaîne vide sans cible attribuée', () => {
    expect(libelleCibles(duel({ cible_haut: null, cible_bas: null }))).toBe('')
  })
})

describe('libelleBouton', () => {
  const impact = (patch: Partial<ResumeLancement>): ResumeLancement => ({
    phase_id: 1,
    numeros: [1, 2],
    cibles: [4, 7],
    nb_duels: 2,
    nb_archers: 4,
    ...patch,
  })

  it('chiffre ce que le bouton déclenche (duels, cibles, archers)', () => {
    expect(libelleBouton(impact({}))).toBe('Lancer — 2 duels · cibles 4, 7 · 4 archers prévenus')
  })

  it('accorde le singulier pour un seul duel', () => {
    expect(libelleBouton(impact({ numeros: [1], cibles: [4], nb_duels: 1, nb_archers: 2 }))).toBe(
      'Lancer — 1 duel · cibles 4 · 2 archers prévenus',
    )
  })

  it('rend null quand rien n’est prêt (bouton désactivé)', () => {
    expect(
      libelleBouton(impact({ numeros: [], cibles: [], nb_duels: 0, nb_archers: 0 })),
    ).toBeNull()
  })
})

describe('actionDuel', () => {
  // Un tableau réaliste : le n°5 attend l'issue du n°3, qui est prêt à partir sur la cible 4.
  const aval = duel({
    numero: 5,
    tour: 2,
    haut: null,
    bas: null,
    participants_connus: false,
    cible_haut: null,
    cible_bas: null,
    cible_attribuee: false,
    sources_en_attente: [3],
    pret_a_lancer: false,
    blocage: 'en attente du duel n°3',
  })
  const amont = duel({ numero: 3 })

  it('ne propose rien sur un duel prêt : il n’a aucun manquement à lever', () => {
    expect(actionDuel(duel({}), [duel({})], 1)).toBeNull()
  })

  it('déplie le duel amont attendu — ses occupants et sa cible, sans quitter l’écran', () => {
    expect(actionDuel(aval, [amont, aval], 1)).toEqual({
      genre: 'sources',
      sources: [
        {
          numero: 3,
          detail: 'Robin Hood vs Will Scarlet · cible 4',
          archers: [
            { archer_id: 1, libelle: 'Robin Hood', numero_duel: 3 },
            { archer_id: 2, libelle: 'Will Scarlet', numero_duel: 3 },
          ],
        },
      ],
    })
  })

  it('déplie les deux duels amont quand le blocage en nomme deux', () => {
    const bloque = duel({
      ...aval,
      sources_en_attente: [3, 4],
      blocage: 'en attente du duel n°3, n°4',
    })
    const quatre = duel({
      numero: 4,
      haut: { archer_id: 7, nom: 'Tuck', prenom: 'Frère' },
      bas: { archer_id: 8, nom: 'Little', prenom: 'John' },
      cible_haut: 7,
      cible_bas: 7,
    })
    const action = actionDuel(bloque, [amont, quatre, bloque], 1)
    expect(action?.genre).toBe('sources')
    expect(action?.genre === 'sources' && action.sources.map((s) => s.numero)).toEqual([3, 4])
  })

  it('n’offre aucun archer à déclarer forfait quand le duel amont n’a pas encore d’occupant', () => {
    const vide = duel({ numero: 3, haut: null, bas: null, participants_connus: false })
    const action = actionDuel(aval, [vide, aval], 1)
    expect(action).toEqual({
      genre: 'sources',
      sources: [{ numero: 3, detail: 'occupants pas encore connus', archers: [] }],
    })
  })

  it('n’offre aucun forfait quand un seul camp du duel amont est connu', () => {
    // ⚠️ tour 2 et sans cible : un match de tour 1 à camp vide est un BYE (exclu des duels à
    // venir), et `place = match.tour == 1` interdit toute cible au-delà — l'état « un camp connu
    // AVEC cible » n'existe pas en production.
    const demi = duel({
      numero: 3,
      tour: 2,
      bas: null,
      participants_connus: false,
      pret_a_lancer: false,
      cible_haut: null,
      cible_bas: null,
    })
    // ⚠️ L'aval passe au tour 3 : une source de tour 2 ne peut pas alimenter un match de tour 2
    // (`VainqueurDe`/`PerdantDe` ne sont engendrés qu'à `tour + 1`).
    const avalTour3 = { ...aval, tour: 3 }
    const action = actionDuel(avalTour3, [demi, avalTour3], 1)
    expect(action).toEqual({
      genre: 'sources',
      // Le duel amont se déplie quand même (CA : « ses occupants, sa cible ») — c'est le camp
      // connu que l'organisateur doit aller chercher. Seul le FORFAIT est refusé.
      sources: [{ numero: 3, detail: 'Robin Hood vs —', archers: [] }],
    })
  })

  it('ne casse pas si le duel amont a disparu de la liste entre deux rafraîchissements', () => {
    expect(actionDuel(aval, [aval], 1)).toEqual({
      genre: 'sources',
      sources: [{ numero: 3, detail: 'plus dans la liste des duels à venir', archers: [] }],
    })
  })

  it('renvoie au plan de duels quand la cible manque AU TOUR POSÉ', () => {
    const sansCible = duel({
      tour: 1,
      cible_haut: null,
      cible_bas: null,
      cible_attribuee: false,
      pret_a_lancer: false,
      blocage: 'cible non attribuée',
    })
    expect(actionDuel(sansCible, [sansCible], 1)).toEqual({ genre: 'placement' })
  })

  it('dit la limite au lieu d’offrir une fausse porte sur un tour NON encore posé', () => {
    const tourDeux = duel({
      numero: 5,
      tour: 2,
      cible_haut: null,
      cible_bas: null,
      cible_attribuee: false,
      pret_a_lancer: false,
      blocage: 'cible non attribuée',
    })
    // Le tour posé est le 1 : le tour 2 n'a pas encore de cibles, aucun geste d'ici ne les pose.
    const action = actionDuel(tourDeux, [tourDeux], 1)
    // Le TEXTE, pas seulement le genre : c'est l'accroche côté front qui doit suivre la garde
    // serveur, sans quoi l'écran annonce une limite abolie et rien ne rougit (DETTE-019).
    expect(action).toEqual({
      genre: 'sans-recours',
      explication: 'Les cibles de ce tour seront posées quand le tour précédent sera terminé.',
    })
  })

  it('offre le plan de duels sur un tour ≥ 2 DEVENU le tour posé (E03US012)', () => {
    // La capacité neuve : passé le premier tour, « cible non attribuée » se répare enfin. Cette
    // même ligne renvoyait « sans-recours » quel que soit l'état du plan.
    const tourDeux = duel({
      numero: 5,
      tour: 2,
      cible_haut: null,
      cible_bas: null,
      cible_attribuee: false,
      pret_a_lancer: false,
      blocage: 'cible non attribuée',
    })
    expect(actionDuel(tourDeux, [tourDeux], 2)).toEqual({ genre: 'placement' })
  })

  it('renvoie au plan de duels quand AUCUN plan n’est lisible (pas de gabarit)', () => {
    // ⚠️ `tour_pose === null` = « aucun plan lisible », pas « tour pas encore posé ». Le geste qui
    // lève le manquement est d'aller appliquer un plan de salle puis générer — c'est le CA
    // d'E16US008. Dire « attendez le tour précédent » sur un tour 1 est faux : il n'y en a pas.
    const sansPlan = duel({
      tour: 1,
      cible_haut: null,
      cible_bas: null,
      cible_attribuee: false,
      pret_a_lancer: false,
      blocage: 'cible non attribuée',
    })
    expect(actionDuel(sansPlan, [sansPlan], null)).toEqual({ genre: 'placement' })
    // Et la raison est bien « aucun plan », pas « tour 1 » : un tour ≥ 2 sans gabarit renvoie
    // au même endroit — c'est là qu'on applique un plan de salle.
    const tourDeuxSansPlan = duel({ ...sansPlan, tour: 2 })
    expect(actionDuel(tourDeuxSansPlan, [tourDeuxSansPlan], null)).toEqual({ genre: 'placement' })
  })

  it('ne propose rien sur « adversaire non déterminé » : rien ne se lève depuis le feu vert', () => {
    const orphelin = duel({
      haut: null,
      bas: null,
      participants_connus: false,
      sources_en_attente: [],
      pret_a_lancer: false,
      blocage: 'adversaire non déterminé',
    })
    expect(actionDuel(orphelin, [orphelin], 1)).toBeNull()
  })
})

describe('archersForfaitables', () => {
  it('aplatit les occupants de tous les duels amont dépliés', () => {
    const sources = [
      { numero: 3, detail: '', archers: [{ archer_id: 1, libelle: 'Robin Hood', numero_duel: 3 }] },
      {
        numero: 4,
        detail: '',
        archers: [{ archer_id: 8, libelle: 'John Little', numero_duel: 4 }],
      },
    ]
    expect(archersForfaitables(sources).map((a) => a.archer_id)).toEqual([1, 8])
  })

  it('rend une liste vide quand aucun occupant n’est connu (pas de bouton à offrir)', () => {
    expect(archersForfaitables([{ numero: 3, detail: '', archers: [] }])).toEqual([])
  })
})
