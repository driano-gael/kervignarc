// Tests de la présentation des tableaux (E07US005), écrits **depuis le CA et la maquette P05**
// avant le composant.
//
// C'est ici que vit la règle de la vue « Mon chemin » — la variante **recommandée** par la maquette
// (« l'archer est le sujet, la compétition est le contexte »). Elle n'est pas un simple filtre :
// elle doit dire, sans jamais mentir, où en est un archer dans un arbre qui n'a de vérité que
// partielle — un duel tiré mais pas validé n'a pas de vainqueur acquis, un adversaire peut n'être
// pas encore sorti de son duel amont, et un archer battu n'est **pas** forcément éliminé depuis que
// la profondeur intégrale (E06US006) fait descendre les perdants dans un tableau de placement.
//
// Le piège que ces tests existent pour empêcher : afficher « éliminé » à quelqu'un qui joue encore,
// ou « à venir » à quelqu'un qui est rentré chez lui. Les deux sont indétectables depuis le code.

import { describe, expect, it } from 'vitest'
import type { DuelPublic, TableauPublic } from './api'
import { cheminDeArcher, libelleEnjeu, libelleTour, parTour, scoreVu } from './presentation'

const MARTIN = { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' }
const DURAND = { archer_id: 2, nom: 'DURAND', prenom: 'Eve' }
const PETIT = { archer_id: 3, nom: 'PETIT', prenom: 'Ana' }

function duel(patch: Partial<DuelPublic> = {}): DuelPublic {
  return {
    numero: 1,
    tour: 1,
    place_en_jeu: null,
    haut: MARTIN,
    bas: DURAND,
    est_bye: false,
    points_haut: null,
    points_bas: null,
    vainqueur: null,
    termine: false,
    validee: false,
    ...patch,
  }
}

function tableau(duels: DuelPublic[], patch: Partial<TableauPublic> = {}): TableauPublic {
  return {
    phase_id: 1,
    ordre: 2,
    type: 'elimination_directe',
    effectif: 8,
    taille: 8,
    nb_tours: 3,
    est_termine: false,
    duels,
    podium: [],
    ...patch,
  }
}

describe('libelleTour', () => {
  it('nomme les derniers tours comme la salle les nomme', () => {
    // Vocabulaire FFTA (règle 3) : personne ne dit « tour 3 sur 3 », on dit « la finale ».
    expect(libelleTour(3, 3)).toBe('Finale')
    expect(libelleTour(2, 3)).toBe('Demi-finales')
    expect(libelleTour(1, 3)).toBe('Quarts de finale')
  })

  it('bascule en fractions au-delà des quarts', () => {
    // Au-delà, la langue n'a plus de mot : « 1/8 de finale » est ce qui est écrit sur les tableaux
    // papier de la fédération, donc ce qu'un archer reconnaît.
    expect(libelleTour(1, 4)).toBe('1/8 de finale')
    expect(libelleTour(1, 5)).toBe('1/16 de finale')
  })
})

describe('libelleEnjeu', () => {
  it('nomme la finale et la petite finale', () => {
    expect(libelleEnjeu([1, 2])).toBe('Finale')
    expect(libelleEnjeu([3, 4])).toBe('Petite finale')
  })

  it('nomme les places au-delà du podium', () => {
    // Le sujet d'E06US006 : sous profondeur intégrale, un match joue les places 5 à 8. Le déduire
    // du numéro de tour serait faux — c'est le même tour que la demi-finale.
    expect(libelleEnjeu([5, 8])).toBe('Places 5 à 8')
    expect(libelleEnjeu([5, 6])).toBe('Places 5-6')
  })

  it('ne nomme rien quand le tableau ne met pas de place en jeu', () => {
    expect(libelleEnjeu(null)).toBeNull()
  })
})

describe('scoreVu', () => {
  it('rend le score du point de vue du camp regardé', () => {
    // « 6 — 2 » et non « 2 — 6 » : dans « mon chemin », l'archer suivi est toujours à gauche.
    const joue = duel({ points_haut: 6, points_bas: 2, termine: true, validee: true })
    expect(scoreVu(joue, 'haut')).toBe('6 — 2')
    expect(scoreVu(joue, 'bas')).toBe('2 — 6')
  })

  it('ne rend rien tant que rien n’est tiré', () => {
    expect(scoreVu(duel(), 'haut')).toBeNull()
  })
})

describe('cheminDeArcher', () => {
  it('ne garde que les matchs de l’archer, dans l’ordre des tours', () => {
    // CA « mon chemin » : l'arbre réduit à la trajectoire de l'archer. Les matchs des autres n'y
    // sont pas — c'est toute la différence avec la vue « arbre complet ».
    const chemin = cheminDeArcher(
      tableau([
        duel({ numero: 2, tour: 1, haut: PETIT, bas: DURAND }),
        duel({ numero: 1, tour: 1, haut: MARTIN, bas: PETIT }),
        duel({ numero: 5, tour: 2, haut: MARTIN, bas: null }),
      ]),
      MARTIN.archer_id,
    )

    expect(chemin.map((e) => e.tour)).toEqual([1, 2, 3])
    expect(chemin[0]?.adversaire).toEqual(PETIT)
  })

  it('marque gagné / perdu seulement quand le duel est validé', () => {
    // **Le piège central.** Un duel tiré mais non validé n'a pas fait avancer l'arbre (le serveur
    // ne rejoue que les duels validés) : afficher « GAGNÉ » à ce moment-là promettrait une
    // qualification que la ligne suivante contredirait aussitôt.
    const tire = tableau([
      duel({ numero: 1, tour: 1, vainqueur: 'haut', termine: true, validee: false }),
    ])
    const scelle = tableau([
      duel({ numero: 1, tour: 1, vainqueur: 'haut', termine: true, validee: true }),
    ])

    expect(cheminDeArcher(tire, MARTIN.archer_id)[0]?.statut).toBe('en_attente')
    expect(cheminDeArcher(scelle, MARTIN.archer_id)[0]?.statut).toBe('gagne')
    expect(cheminDeArcher(scelle, DURAND.archer_id)[0]?.statut).toBe('perdu')
  })

  it('annonce les tours restants tant que l’archer n’est pas sorti', () => {
    // La 3ᵉ ligne de la maquette P05 : « 1/2 · — · À VENIR ». L'archer n'y est pas encore placé,
    // mais son tableau a encore des tours — les taire ferait croire que sa journée s'arrête là.
    const chemin = cheminDeArcher(
      tableau([duel({ numero: 1, tour: 1, vainqueur: 'haut', termine: true, validee: true })]),
      MARTIN.archer_id,
    )

    expect(chemin.map((e) => e.statut)).toEqual(['gagne', 'a_venir', 'a_venir'])
    expect(chemin.map((e) => e.tour)).toEqual([1, 2, 3])
  })

  it('n’annonce aucun tour à venir à un archer battu et sorti', () => {
    // Le piège symétrique : lui promettre des tours qu'il ne jouera pas. Il est sorti **parce
    // qu'aucun match ultérieur ne le porte**, pas parce qu'il a perdu — nuance qui compte, cf. le
    // test suivant.
    const chemin = cheminDeArcher(
      tableau([duel({ numero: 1, tour: 1, vainqueur: 'haut', termine: true, validee: true })]),
      DURAND.archer_id,
    )

    expect(chemin.map((e) => e.statut)).toEqual(['perdu'])
  })

  it('suit le perdant qui descend dans le tableau de placement', () => {
    // E06US006 : sous profondeur intégrale, perdre ne veut plus dire rentrer chez soi. Le serveur
    // place le battu dans son sous-tableau ; le chemin doit le suivre là-bas plutôt que de
    // s'arrêter sur la défaite — sinon la vue annonce « éliminé » à quelqu'un qui tire encore.
    const chemin = cheminDeArcher(
      tableau([
        duel({ numero: 1, tour: 1, vainqueur: 'haut', termine: true, validee: true }),
        duel({ numero: 6, tour: 2, place_en_jeu: [5, 8], haut: DURAND, bas: PETIT }),
      ]),
      DURAND.archer_id,
    )

    expect(chemin.map((e) => e.statut)).toEqual(['perdu', 'a_jouer', 'a_venir'])
    expect(chemin[1]?.enjeu).toBe('Places 5 à 8')
  })

  it('distingue « adversaire pas encore connu » de « à jouer »', () => {
    // L'archer **est** placé au tour suivant, mais son adversaire sort d'un duel amont non tranché.
    // Afficher un tiret sans le dire laisserait croire à un exempt.
    const chemin = cheminDeArcher(
      tableau([duel({ numero: 5, tour: 2, haut: MARTIN, bas: null })]),
      MARTIN.archer_id,
    )

    expect(chemin[0]?.statut).toBe('attente_adversaire')
  })

  it('nomme l’exempt plutôt que de le faire passer pour un duel gagné', () => {
    // Un bye n'est pas une victoire : il n'y a eu personne en face. Le dire évite qu'un archer
    // cherche un score qui n'existe pas.
    const chemin = cheminDeArcher(
      tableau([duel({ numero: 1, tour: 1, bas: null, est_bye: true })]),
      MARTIN.archer_id,
    )

    expect(chemin[0]?.statut).toBe('exempt')
  })

  it('rend un chemin vide pour un archer absent du tableau', () => {
    // Un archer suivi qui n'est pas dans cette phase (autre catégorie, éliminé en qualification) :
    // la vue doit pouvoir le dire, pas afficher un chemin fantôme.
    expect(cheminDeArcher(tableau([duel()]), 99)).toEqual([])
  })
})

describe('parTour', () => {
  it('groupe les matchs par tour, dans l’ordre, en nommant chaque tour', () => {
    // Variante B de la maquette : « l'arbre en vraies branches ne tient pas [sur 360 px] ; en
    // **liste par tour**, si ». Le groupement est donc la concession mobile assumée.
    const groupes = parTour(
      tableau([
        duel({ numero: 5, tour: 2 }),
        duel({ numero: 2, tour: 1 }),
        duel({ numero: 1, tour: 1 }),
      ]),
    )

    expect(groupes.map((g) => g.tour)).toEqual([1, 2])
    expect(groupes[0]?.libelle).toBe('Quarts de finale')
    expect(groupes[0]?.duels.map((d) => d.numero)).toEqual([1, 2])
  })

  it('écarte les exempts, qui ne sont pas des matchs à regarder', () => {
    // Un bye occupe une place de l'arbre mais ne se tire pas : le lister ferait chercher une
    // rencontre qui n'aura pas lieu. Même filtre que le suivi du déroulé (E07US004).
    const groupes = parTour(
      tableau([
        duel({ numero: 1, tour: 1 }),
        duel({ numero: 2, tour: 1, est_bye: true, bas: null }),
      ]),
    )

    expect(groupes[0]?.duels.map((d) => d.numero)).toEqual([1])
  })
})
