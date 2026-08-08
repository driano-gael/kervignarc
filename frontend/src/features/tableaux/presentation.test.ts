// Tests de la présentation des tableaux (E07US005).
//
// C'est ici que vit la règle de la vue « Mon chemin » — la variante **recommandée** par la maquette
// P05 (« l'archer est le sujet, la compétition est le contexte »). Elle n'est pas un simple filtre :
// elle doit dire, sans jamais mentir, où en est un archer dans un arbre qui n'a de vérité que
// partielle — un duel tiré mais pas validé n'a pas de vainqueur acquis, un adversaire peut n'être
// pas encore sorti de son duel amont, et un archer battu n'est **pas** forcément éliminé depuis que
// la profondeur intégrale (E06US006) fait descendre les perdants dans un tableau de placement.
//
// Le piège que ces tests existent pour empêcher : afficher « éliminé » à quelqu'un qui joue encore,
// ou « à venir » à quelqu'un qui est rentré chez lui. Les deux sont indétectables depuis le code.
//
// ⚠️ **Les fixtures reproduisent le DTO réel, et c'est un correctif de revue.** Un premier jet
// posait `place_en_jeu: [5, 8]` sur un match de tour 2 — une valeur que le serveur **ne produit
// jamais** (`place_en_jeu` n'existe que sur les matchs terminaux, `domain/tableau.py`). Les tests
// passaient donc sur une fiction et masquaient le vrai comportement : « Demi-finales » affiché sur
// un match des places 5-8. Toute fixture ajoutée ici doit rester une **sortie possible du
// serveur** ; en cas de doute, faire tourner le domaine plutôt que de l'imaginer.

import { describe, expect, it } from 'vitest'
import type { DuelPublic, TableauPublic } from './api'
import { cheminDeArcher, parcoursToutesPhases, parTour, scoreVu } from './presentation'

const MARTIN = { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' }
const DURAND = { archer_id: 2, nom: 'DURAND', prenom: 'Eve' }
const PETIT = { archer_id: 3, nom: 'PETIT', prenom: 'Ana' }

function duel(patch: Partial<DuelPublic> = {}): DuelPublic {
  return {
    numero: 1,
    tour: 1,
    libelle: 'Quart de finale',
    place_en_jeu: null,
    plage: [1, 8],
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

/** Le tour 2 d'un tableau de 8 en profondeur **podium** : deux demi-finales, rien d'autre. */
const DEMIES = [
  duel({ numero: 5, tour: 2, libelle: 'Demi-finale', plage: [1, 4], haut: null, bas: null }),
  duel({ numero: 6, tour: 2, libelle: 'Demi-finale', plage: [1, 4], haut: null, bas: null }),
]

/** Le dernier tour d'un tableau de 8 en profondeur **podium** — le réglage par défaut du projet.
 * Il porte **toujours deux** matchs : `PlacementEnCascade` fait rejouer les perdants des demies en
 * petite finale. Un décor à finale seule n'existe qu'en profondeur `top(2)` — un test qui en
 * fabriquerait un consacrerait un comportement que la production ne produit jamais. */
const PODIUM_T2_T3 = [
  duel({ numero: 5, tour: 2, libelle: 'Demi-finale', plage: [1, 4], haut: null, bas: null }),
  duel({ numero: 6, tour: 2, libelle: 'Demi-finale', plage: [1, 4], haut: null, bas: null }),
  duel({
    numero: 7,
    tour: 3,
    libelle: 'Finale',
    place_en_jeu: [1, 2],
    plage: [1, 2],
    haut: null,
    bas: null,
  }),
  duel({
    numero: 8,
    tour: 3,
    libelle: 'Petite finale',
    place_en_jeu: [3, 4],
    plage: [3, 4],
    haut: null,
    bas: null,
  }),
]

/** Les quatre matchs terminaux d'un tableau de 8 en profondeur **intégrale** (tour 3). */
const FINALES_INTEGRALE = [
  ...PODIUM_T2_T3.filter((d) => d.tour === 3),
  duel({
    numero: 11,
    tour: 3,
    libelle: 'Match pour la 5ᵉ place',
    place_en_jeu: [5, 6],
    plage: [5, 6],
    haut: null,
    bas: null,
  }),
  duel({
    numero: 12,
    tour: 3,
    libelle: 'Match pour la 7ᵉ place',
    place_en_jeu: [7, 8],
    plage: [7, 8],
    haut: null,
    bas: null,
  }),
]

/** Les deux matchs du sous-tableau des places 5-8, tels que le serveur les émet réellement :
 * `place_en_jeu` **null** (non terminaux) et `plage` `[5, 8]`, au même tour que les demies. */
const PLACEMENT_5_8 = [
  duel({ numero: 9, tour: 2, libelle: 'Places 5 à 8', plage: [5, 8], haut: DURAND, bas: PETIT }),
  duel({ numero: 10, tour: 2, libelle: 'Places 5 à 8', plage: [5, 8], haut: null, bas: null }),
]

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
        duel({
          numero: 5,
          tour: 2,
          libelle: 'Demi-finale',
          plage: [1, 4],
          haut: MARTIN,
          bas: null,
        }),
      ]),
      MARTIN.archer_id,
    )

    expect(chemin.map((e) => e.tour)).toEqual([1, 2, 3])
    expect(chemin[0]?.adversaire).toEqual(PETIT)
  })

  it('reprend le nom du match tel que le serveur le donne', () => {
    // Le vocabulaire n'est **pas** recalculé ici (règle 3, `DETTE-020`) : ce test verrouille le fait
    // que la présentation se contente de relayer. S'il échoue parce qu'on a « amélioré » un libellé
    // côté client, c'est le client qu'il faut corriger, pas le test.
    const chemin = cheminDeArcher(
      tableau([duel({ numero: 11, tour: 3, libelle: 'Petite finale', place_en_jeu: [3, 4] })]),
      MARTIN.archer_id,
    )

    expect(chemin[0]?.libelle).toBe('Petite finale')
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

  it('annonce les tours restants, en nommant toutes les suites possibles', () => {
    // La 3ᵉ ligne de la maquette P05 : « 1/2 · — · À VENIR ». L'archer n'y est pas encore placé,
    // mais son tableau a encore des tours — les taire ferait croire que sa journée s'arrête là.
    //
    // ⚠️ **Le décor est celui de la production.** Un premier jet ne mettait que la finale au tour 3
    // — un arbre que le serveur ne produit jamais — et consacrait ainsi un comportement qui ne
    // fonctionnait dans **aucune** configuration réelle : en profondeur podium comme en intégrale,
    // le dernier tour porte toujours au moins deux branches. C'est l'erreur que l'en-tête de ce
    // fichier interdit, refaite dans le fichier même qui l'interdit ; d'où cette note.
    const chemin = cheminDeArcher(
      tableau([
        duel({ numero: 1, tour: 1, vainqueur: 'haut', termine: true, validee: true }),
        ...PODIUM_T2_T3,
      ]),
      MARTIN.archer_id,
    )

    expect(chemin.map((e) => e.statut)).toEqual(['gagne', 'a_venir', 'a_venir'])
    // Le tour 2 n'a qu'une suite ; le tour 3 en a deux, et **les deux sont vraies**. Les nommer
    // toutes les deux informe ; n'en nommer aucune — le comportement du premier correctif —
    // laissait la dernière ligne anonyme sur tous les tournois standards.
    expect(chemin.map((e) => e.libelle)).toEqual([
      'Quart de finale',
      'Demi-finale',
      'Finale ou Petite finale',
    ])
  })

  it('cesse de nommer quand les suites possibles se multiplient', () => {
    // À deux tours de distance sous placement intégral, quatre branches sont atteignables : une
    // énumération de quatre libellés n'informe plus, elle encombre. La ligne dit alors « à venir »
    // sans nom — omission assumée, et **bornée à ce cas**, ce qui est toute la différence avec le
    // premier correctif.
    const chemin = cheminDeArcher(
      tableau([duel({ numero: 1, tour: 1 }), ...DEMIES, ...PLACEMENT_5_8, ...FINALES_INTEGRALE]),
      MARTIN.archer_id,
    )

    expect(chemin[1]?.libelle).toBe('Demi-finale ou Places 5 à 8')
    expect(chemin[2]?.libelle).toBeNull()
  })

  it('nomme les deux suites possibles quand la branche n’est pas décidée', () => {
    // Sous profondeur intégrale, le tour 2 porte **deux** branches : les demi-finales et les places
    // 5-8. Un archer dont le quart n'est pas tranché peut aller dans l'une ou l'autre — le nommer
    // « Demi-finale » lui promettrait un podium, le nommer « Places 5 à 8 » l'enterrerait. Les deux
    // sont vrais : c'est exactement ce qu'il peut encore atteindre.
    const chemin = cheminDeArcher(
      tableau([duel({ numero: 1, tour: 1 }), ...DEMIES, ...PLACEMENT_5_8]),
      MARTIN.archer_id,
    )

    expect(chemin[0]?.statut).toBe('a_jouer')
    expect(chemin[1]?.statut).toBe('a_venir')
    expect(chemin[1]?.libelle).toBe('Demi-finale ou Places 5 à 8')
  })

  it('n’annonce aucun tour à venir à un archer battu et sorti', () => {
    // Le piège symétrique : lui promettre des tours qu'il ne jouera pas.
    const chemin = cheminDeArcher(
      tableau([
        duel({ numero: 1, tour: 1, vainqueur: 'haut', termine: true, validee: true }),
        ...DEMIES,
      ]),
      DURAND.archer_id,
    )

    expect(chemin.map((e) => e.statut)).toEqual(['perdu'])
  })

  it('n’annonce aucun tour à venir tant que la défaite n’est pas validée', () => {
    // **Cas adverse relevé en revue.** Un premier jet ne fermait le parcours que sur `perdu` : un
    // archer battu 0-6, dont le scoreur n'avait pas encore scellé, lisait « Demi-finale · À venir »
    // puis « Finale · À venir » juste sous son score. Tant que rien n'est acquis, on ne promet
    // rien — ni la sortie, ni la suite.
    const chemin = cheminDeArcher(
      tableau([
        duel({
          numero: 1,
          tour: 1,
          points_haut: 6,
          points_bas: 0,
          vainqueur: 'haut',
          termine: true,
          validee: false,
        }),
        ...DEMIES,
      ]),
      DURAND.archer_id,
    )

    expect(chemin.map((e) => e.statut)).toEqual(['en_attente'])
  })

  it('suit le perdant qui descend en placement, sans le dire demi-finaliste', () => {
    // E06US006 : sous profondeur intégrale, perdre ne veut plus dire rentrer chez soi. Le serveur
    // place le battu dans son sous-tableau ; le chemin doit le suivre là-bas **et le nommer
    // correctement**. C'est le défaut trouvé en revue : `place_en_jeu` étant `null` sur ce match
    // (non terminal), un libellé recalculé côté client affichait « Demi-finales ».
    const chemin = cheminDeArcher(
      tableau([
        duel({ numero: 1, tour: 1, vainqueur: 'haut', termine: true, validee: true }),
        ...DEMIES,
        ...PLACEMENT_5_8,
        ...FINALES_INTEGRALE,
      ]),
      DURAND.archer_id,
    )

    expect(chemin.map((e) => e.statut)).toEqual(['perdu', 'a_jouer', 'a_venir'])
    expect(chemin[1]?.libelle).toBe('Places 5 à 8')
    // Son tour 3 : les matchs `[5,6]` et `[7,8]` existent bel et bien dans un vrai arbre — ce sont
    // eux qu'il peut atteindre. Ce qu'il ne peut **pas** atteindre, c'est la finale, et c'est
    // `inclus()` qui l'écarte. Jamais « Finale » pour un archer parti en placement.
    expect(chemin[2]?.libelle).toBe('Match pour la 5ᵉ place ou Match pour la 7ᵉ place')
  })

  it('distingue « adversaire pas encore connu » de « à jouer »', () => {
    // L'archer **est** placé au tour suivant, mais son adversaire sort d'un duel amont non tranché.
    // Afficher un tiret sans le dire laisserait croire à un exempt.
    const chemin = cheminDeArcher(
      tableau([
        duel({
          numero: 5,
          tour: 2,
          libelle: 'Demi-finale',
          plage: [1, 4],
          haut: MARTIN,
          bas: null,
        }),
      ]),
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
  it('groupe par branche et non par numéro de tour', () => {
    // **Correctif de revue.** La fonction jumelle de la saisie (`saisie-duels/duel.ts`) documente
    // déjà ce piège : la petite finale se dispute au **même tour** que la finale, et un groupement
    // par tour brut la range sous l'en-tête « Finale ». Sous profondeur intégrale c'était pire —
    // les matchs des places 5-8 atterrissaient sous « Demi-finales ».
    const groupes = parTour(
      tableau([
        duel({ numero: 11, tour: 3, libelle: 'Finale', place_en_jeu: [1, 2], plage: [1, 2] }),
        duel({
          numero: 12,
          tour: 3,
          libelle: 'Petite finale',
          place_en_jeu: [3, 4],
          plage: [3, 4],
        }),
        ...DEMIES.map((d) => ({ ...d, haut: MARTIN })),
      ]),
    )

    expect(groupes.map((g) => g.libelle)).toEqual(['Demi-finale', 'Finale', 'Petite finale'])
    expect(groupes[1]?.duels.map((d) => d.numero)).toEqual([11])
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

  it('écarte les matchs dont aucun occupant n’est connu', () => {
    // **Correctif de revue.** L'arbre porte tous ses matchs dès la construction : à 9 h, les tours
    // au-delà du premier n'ont aucun occupant, et l'écran projeté affichait des suites de lignes
    // « — vs — » qui n'apprennent rien à personne.
    const groupes = parTour(tableau([duel({ numero: 1, tour: 1 }), ...DEMIES]))

    expect(groupes.map((g) => g.libelle)).toEqual(['Quart de finale'])
  })
})

// E16US004, **dérivé du CA** « récapitulatif repliable de la journée, couvrant tous les tours de
// toutes les phases joués » (questionnaire P02 : *« on doit pouvoir retrouver tous les tours de
// toutes les phases joués »*). Écrit avant le câblage de l'écran (règle 9).
//
// La lecture est **rétrospective** : le récapitulatif dit ce qui s'est passé. Ce qui reste à jouer
// est déjà porté par le bloc « Ensuite » de la carte de suivi (E07US008) ; le répéter ici ferait
// deux réponses à la même question, désynchronisées au premier écart.
describe('parcoursToutesPhases — le récapitulatif de la journée d’un archer', () => {
  const gagne = (patch: Partial<DuelPublic>) =>
    duel({
      points_haut: 6,
      points_bas: 2,
      vainqueur: 'haut',
      termine: true,
      validee: true,
      ...patch,
    })

  it('rend une entrée par phase où l’archer a réellement tiré, dans l’ordre des phases', () => {
    const principal = tableau([gagne({ numero: 1, tour: 1 })], { phase_id: 10, ordre: 2 })
    const placement = tableau([gagne({ numero: 1, tour: 1, libelle: 'Places 5 à 8' })], {
      phase_id: 11,
      ordre: 3,
    })

    const parcours = parcoursToutesPhases([placement, principal], MARTIN.archer_id)

    expect(parcours.map((p) => p.phaseId)).toEqual([10, 11])
  })

  it('écarte une phase où l’archer n’apparaît pas', () => {
    // Il n'est pas dans toutes les catégories ni dans tous les tableaux : une section vide
    // « Élimination directe — rien » ferait chercher une erreur là où il n'y en a pas.
    const sien = tableau([gagne({ numero: 1, tour: 1 })], { phase_id: 10, ordre: 2 })
    const autre = tableau([gagne({ numero: 1, tour: 1, haut: PETIT, bas: DURAND })], {
      phase_id: 11,
      ordre: 3,
    })

    expect(parcoursToutesPhases([sien, autre], MARTIN.archer_id).map((p) => p.phaseId)).toEqual([
      10,
    ])
  })

  it('retient tous les tours joués d’une phase, dans l’ordre', () => {
    const arbre = tableau(
      [
        gagne({ numero: 1, tour: 1, libelle: 'Huitième de finale' }),
        gagne({ numero: 2, tour: 2, libelle: 'Quart de finale' }),
      ],
      { phase_id: 10, nb_tours: 4 },
    )

    expect(
      parcoursToutesPhases([arbre], MARTIN.archer_id)[0]?.etapes.map((e) => e.libelle),
    ).toEqual(['Huitième de finale', 'Quart de finale'])
  })

  it('n’annonce pas les tours à venir — le récapitulatif regarde en arrière', () => {
    // `cheminDeArcher` prolonge le chemin par des étapes `a_venir` (c'est ce que veut la vue
    // « Mon chemin »). Le récapitulatif, lui, les écarte : « Finale · À venir » sous un titre
    // « ce qui s'est passé » est une promesse, pas un fait.
    const arbre = tableau([gagne({ numero: 1, tour: 1 })], { phase_id: 10, nb_tours: 3 })

    const etapes = parcoursToutesPhases([arbre], MARTIN.archer_id)[0]?.etapes ?? []

    expect(etapes.every((e) => e.statut !== 'a_venir')).toBe(true)
    expect(etapes).toHaveLength(1)
  })

  it('garde un exempt : il explique un tour sauté', () => {
    const arbre = tableau(
      [
        duel({ numero: 1, tour: 1, est_bye: true, bas: null }),
        gagne({ numero: 2, tour: 2, libelle: 'Quart de finale' }),
      ],
      { phase_id: 10, nb_tours: 3 },
    )

    expect(parcoursToutesPhases([arbre], MARTIN.archer_id)[0]?.etapes.map((e) => e.statut)).toEqual(
      ['exempt', 'gagne'],
    )
  })

  it('garde un duel tiré mais pas encore validé, avec son statut d’attente', () => {
    // Le score est là, le scoreur n'a pas scellé : le taire ferait disparaître de la journée un
    // match que l'archer vient de tirer. C'est le statut qui porte la réserve, pas l'absence.
    const arbre = tableau(
      [duel({ numero: 1, tour: 1, points_haut: 6, points_bas: 4, termine: true, validee: false })],
      { phase_id: 10 },
    )

    expect(parcoursToutesPhases([arbre], MARTIN.archer_id)[0]?.etapes.map((e) => e.statut)).toEqual(
      ['en_attente'],
    )
  })

  it('écarte une phase où l’archer n’a qu’un match encore à tirer', () => {
    // Rien ne s'est passé : sa place est annoncée par « Ensuite », pas par le récapitulatif.
    const arbre = tableau([duel({ numero: 1, tour: 1 })], { phase_id: 10 })

    expect(parcoursToutesPhases([arbre], MARTIN.archer_id)).toEqual([])
  })
})
