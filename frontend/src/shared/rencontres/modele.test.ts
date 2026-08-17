// Tests du modèle neutre des formats sans arbre (E05US031, ADR-0089 §2).
//
// C'est ici que vit la règle de « mon chemin » pour les poules et le système suisse — celle qui doit
// dire où en est un archer dans un format **qui n'a pas d'arbre**, donc où rien ne se déduit d'une
// branche. Les pièges sont les mêmes que ceux de l'arbre, et deux d'entre eux ont déjà coûté une
// passe de revue là-bas :
//
//  1. une rencontre **tirée mais pas validée** n'a pas de vainqueur acquis — l'annoncer promettrait
//     un rang de poule que la ligne suivante dément ;
//  2. **« aucun de vos archers ici » n'est pas « rien à afficher »** — c'est le cas banal du
//     spectateur qui suit une catégorie et regarde la poule d'une autre.
//
// ⚠️ **Les fixtures reproduisent le DTO réel.** Elles se construisent par les `mk*` ci-dessous, dont
// les défauts sont ceux du serveur : une rencontre non tirée a `points_* = null`, `termine = false`,
// `validee = false` et `vainqueur = null`. Fabriquer un état que le serveur ne produit jamais ferait
// passer les tests sur une fiction — le défaut exact qu'a corrigé la revue d'E07US005.

import { describe, expect, it } from 'vitest'
import {
  cheminDe,
  coteDe,
  engagesParmi,
  nomDeArcher,
  rangDe,
  scoreVu,
  statutDe,
  type ArcherPublic,
  type BlocRencontres,
  type FormatPublic,
  type RencontreVue,
  type TourVue,
} from './modele'

const MARTIN: ArcherPublic = { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' }
const DURAND: ArcherPublic = { archer_id: 2, nom: 'DURAND', prenom: 'Eve' }
const PETIT: ArcherPublic = { archer_id: 3, nom: 'PETIT', prenom: 'Ana' }

function mkRencontre(over: Partial<RencontreVue> = {}): RencontreVue {
  return {
    numero: 1,
    haut: MARTIN,
    bas: DURAND,
    couloirs: null,
    points_haut: null,
    points_bas: null,
    vainqueur: null,
    termine: false,
    validee: false,
    bloquee: false,
    ...over,
  }
}

function mkTour(over: Partial<TourVue> = {}): TourVue {
  return { libelle: 'Tour 1', rencontres: [mkRencontre()], exempt: null, clos: false, ...over }
}

function mkBloc(over: Partial<BlocRencontres> = {}): BlocRencontres {
  return {
    cle: 'bloc',
    titre: null,
    tours: [mkTour()],
    colonnes: [{ cle: 'pts', libelle: 'Pts', aide: 'Points.' }],
    classement: [],
    notes: [],
    ...over,
  }
}

function mkFormat(blocs: BlocRencontres[]): FormatPublic {
  return { blocs, conflits: [] }
}

describe('coteDe / scoreVu', () => {
  it('rend le score du point de vue de l’archer suivi, jamais dans l’ordre du serveur', () => {
    const rencontre = mkRencontre({ points_haut: 6, points_bas: 2 })

    expect(scoreVu(rencontre, 'haut')).toBe('6 — 2')
    // Le même score, vu de l'autre camp. C'est cette inversion qui fait qu'un archer suivi lit
    // toujours son propre total à gauche — sinon « 2 — 6 » se lit comme une défaite chez le gagnant.
    expect(scoreVu(rencontre, 'bas')).toBe('2 — 6')
  })

  it('ne rend aucun score tant que rien n’est tiré', () => {
    expect(scoreVu(mkRencontre(), 'haut')).toBeNull()
  })

  it('ne reconnaît pas un archer absent de la rencontre', () => {
    expect(coteDe(mkRencontre(), PETIT.archer_id)).toBeNull()
  })
})

describe('statutDe', () => {
  it('n’annonce pas de vainqueur tant que le scoreur n’a pas validé', () => {
    // Piège n°1 : le tir est allé au bout (`termine`), mais rien n'est acquis. Annoncer « gagné »
    // ici promettrait un rang de poule que la validation peut encore démentir.
    const tiree = mkRencontre({ termine: true, vainqueur: 'haut', points_haut: 6, points_bas: 0 })

    expect(statutDe(tiree, 'haut')).toBe('en_attente')
    expect(statutDe(tiree, 'bas')).toBe('en_attente')
  })

  it('tranche une fois la rencontre validée', () => {
    const validee = mkRencontre({ termine: true, validee: true, vainqueur: 'haut' })

    expect(statutDe(validee, 'haut')).toBe('gagne')
    expect(statutDe(validee, 'bas')).toBe('perdu')
  })

  it('rend une rencontre bloquée « à tirer » et non « à valider »', () => {
    // Le serveur masque le tir d'une rencontre désynchronisée et refuse de l'écraser : rien n'est
    // acquis. La dire « en attente de validation » laisserait croire qu'un scoreur va la sceller.
    const bloquee = mkRencontre({ termine: true, validee: true, vainqueur: 'haut', bloquee: true })

    expect(statutDe(bloquee, 'haut')).toBe('a_jouer')
  })

  it('distingue « à tirer » de « adversaire à désigner »', () => {
    expect(statutDe(mkRencontre(), 'haut')).toBe('a_jouer')
    expect(statutDe(mkRencontre({ bas: null }), 'haut')).toBe('attente_adversaire')
  })
})

describe('cheminDe', () => {
  it('suit un archer tour après tour, dans l’ordre', () => {
    const format = mkFormat([
      mkBloc({
        tours: [
          mkTour({
            libelle: 'Ronde 1',
            rencontres: [
              mkRencontre({
                validee: true,
                termine: true,
                vainqueur: 'haut',
                points_haut: 6,
                points_bas: 2,
              }),
            ],
            clos: true,
          }),
          mkTour({
            libelle: 'Ronde 2',
            rencontres: [mkRencontre({ numero: 2, haut: PETIT, bas: MARTIN })],
          }),
        ],
      }),
    ])

    const chemin = cheminDe(format, MARTIN.archer_id)

    expect(chemin.map((e) => [e.libelle, e.statut, e.score])).toEqual([
      ['Ronde 1', 'gagne', '6 — 2'],
      // Au tour 2, MARTIN est en bas : le score doit rester à sa main — ici rien n'est tiré.
      ['Ronde 2', 'a_jouer', null],
    ])
    expect(chemin[1]?.adversaire).toEqual(PETIT)
  })

  it('porte le bye comme une étape, et non comme un trou', () => {
    // Un archer exempt d'une ronde n'a pas tiré. L'omettre laisserait un trou inexpliqué dans un
    // chemin par ailleurs continu — le spectateur chercherait une rencontre qui n'a pas eu lieu.
    const format = mkFormat([
      mkBloc({
        tours: [mkTour({ libelle: 'Ronde 1', rencontres: [], exempt: PETIT, clos: true })],
      }),
    ])

    expect(cheminDe(format, PETIT.archer_id)).toEqual([
      { libelle: 'Ronde 1', bloc: null, adversaire: null, statut: 'exempt', score: null },
    ])
  })

  it('ne fabrique aucune étape « à venir »', () => {
    // ⚠️ Différence assumée avec l'arbre (cf. l'en-tête de `cheminDe`) : dans un système suisse, la
    // ronde N+1 n'existe pas tant que la N n'est pas close, et son appariement en dépend. Promettre
    // « Ronde 2 · À venir » affirmerait qu'elle aura lieu **et** qu'il n'y a personne en face.
    const format = mkFormat([mkBloc({ tours: [mkTour({ libelle: 'Ronde 1' })] })])

    expect(cheminDe(format, MARTIN.archer_id)).toHaveLength(1)
  })

  it('nomme le bloc quand le format en a plusieurs', () => {
    const format = mkFormat([mkBloc({ cle: 'p1', titre: 'Poule 1' })])

    expect(cheminDe(format, MARTIN.archer_id)[0]?.bloc).toBe('Poule 1')
  })

  it('rend un chemin vide pour un archer absent de la phase', () => {
    expect(cheminDe(mkFormat([mkBloc()]), 99)).toEqual([])
  })
})

describe('rangDe / nomDeArcher / engagesParmi', () => {
  const classe = mkFormat([
    mkBloc({
      titre: 'Poule 2',
      classement: [
        {
          rang: 1,
          archer_id: MARTIN.archer_id,
          nom: 'Luc MARTIN',
          valeurs: ['4'],
          ex_aequo: false,
        },
        { rang: 2, archer_id: DURAND.archer_id, nom: 'Eve DURAND', valeurs: ['2'], ex_aequo: true },
      ],
    }),
  ])

  it('rend le rang et le bloc qui le porte', () => {
    const trouve = rangDe(classe, DURAND.archer_id)

    expect(trouve?.bloc.titre).toBe('Poule 2')
    expect(trouve?.ligne.rang).toBe(2)
    expect(trouve?.ligne.ex_aequo).toBe(true)
  })

  it('lit le nom dans la phase, jamais dans un cache client', () => {
    expect(nomDeArcher(classe, MARTIN.archer_id)).toBe('Luc MARTIN')
    // Sans classement, le nom se relève sur les appariements — le cas d'une phase qui vient de
    // démarrer, où personne n'est encore classé.
    expect(nomDeArcher(mkFormat([mkBloc()]), DURAND.archer_id)).toBe('Eve DURAND')
    expect(nomDeArcher(classe, 99)).toBeNull()
  })

  it('ne retient que les archers suivis réellement engagés', () => {
    // C'est ce qui permet à la vue de distinguer « aucun de vos archers ici » de « rien du tout » —
    // la distinction qu'E16US004 avait manquée sur l'arbre, et qui est ici couverte dès l'origine.
    expect(engagesParmi(classe, [MARTIN.archer_id, 99, DURAND.archer_id])).toEqual([
      MARTIN.archer_id,
      DURAND.archer_id,
    ])
    expect(engagesParmi(classe, [99])).toEqual([])
  })

  it('compte comme engagé un archer classé qui n’a encore disputé aucune rencontre', () => {
    // Cas réel d'un système suisse dont la ronde 1 vient d'être appariée sans qu'un tir n'ait eu
    // lieu : le classement existe (tout le monde à zéro), les rencontres ne sont pas jouées. Ne
    // regarder que le chemin dirait « aucun de vos archers ici » sur une phase où ils sont tous.
    const sansRencontre = mkFormat([
      mkBloc({
        tours: [],
        classement: [
          {
            rang: 1,
            archer_id: PETIT.archer_id,
            nom: 'Ana PETIT',
            valeurs: ['0'],
            ex_aequo: false,
          },
        ],
      }),
    ])

    expect(engagesParmi(sansRencontre, [PETIT.archer_id])).toEqual([PETIT.archer_id])
  })
})
