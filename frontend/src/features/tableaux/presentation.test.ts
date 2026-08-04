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
import { cheminDeArcher, parTour, scoreVu } from './presentation'

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

  it('annonce les tours restants, nommés par les matchs réels de la branche', () => {
    // La 3ᵉ ligne de la maquette P05 : « 1/2 · — · À VENIR ». L'archer n'y est pas encore placé,
    // mais son tableau a encore des tours — les taire ferait croire que sa journée s'arrête là.
    // Le nom du tour est **lu** sur les matchs réels de ce tour, jamais recalculé.
    const chemin = cheminDeArcher(
      tableau([
        duel({ numero: 1, tour: 1, vainqueur: 'haut', termine: true, validee: true }),
        ...DEMIES,
        duel({
          numero: 11,
          tour: 3,
          libelle: 'Finale',
          place_en_jeu: [1, 2],
          plage: [1, 2],
          haut: null,
          bas: null,
        }),
      ]),
      MARTIN.archer_id,
    )

    expect(chemin.map((e) => e.statut)).toEqual(['gagne', 'a_venir', 'a_venir'])
    expect(chemin.map((e) => e.libelle)).toEqual(['Quart de finale', 'Demi-finale', 'Finale'])
  })

  it('ne nomme pas un tour à venir quand la branche n’est pas décidée', () => {
    // Sous profondeur intégrale, le tour 2 porte **deux** branches : les demi-finales et les places
    // 5-8. Un archer dont le quart n'est pas tranché peut aller dans l'une ou l'autre — le nommer
    // « Demi-finale » lui promettrait un podium, le nommer « Places 5 à 8 » l'enterrerait. On ne
    // nomme donc rien, et la vue affiche « À venir ». C'est le seul cas où la maquette ne peut pas
    // être honorée : elle supposait une seule suite possible.
    const chemin = cheminDeArcher(
      tableau([duel({ numero: 1, tour: 1 }), ...DEMIES, ...PLACEMENT_5_8]),
      MARTIN.archer_id,
    )

    expect(chemin[0]?.statut).toBe('a_jouer')
    expect(chemin[1]?.statut).toBe('a_venir')
    expect(chemin[1]?.libelle).toBeNull()
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
      ]),
      DURAND.archer_id,
    )

    expect(chemin.map((e) => e.statut)).toEqual(['perdu', 'a_jouer', 'a_venir'])
    expect(chemin[1]?.libelle).toBe('Places 5 à 8')
    // Le tour 3 de sa branche : les matchs `[5,6]` et `[7,8]` n'existent pas dans ce décor, donc
    // rien à lire — « À venir » sans nom, plutôt que « Finale ».
    expect(chemin[2]?.libelle).toBeNull()
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
