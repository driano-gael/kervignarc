// Tests de l'adaptation publique du **système suisse** (E05US031).
//
// Le point qui justifie ce fichier à lui seul : `points` et `buchholz` circulent en **demi-points
// doublés** (une victoire vaut 2, un nul 1). Le domaine évite ainsi le flottant, dont les égalités
// approchées sont exactement ce sur quoi un départage ne doit pas reposer — mais cela veut dire que
// **l'affichage brut est faux d'un facteur deux**. Un archer à trois victoires lirait « 6 points »
// dans un format où le maximum est 5. Le rendu de la moitié est donc une règle métier, pas une mise
// en forme, et elle s'exerce ici.

import { describe, expect, it } from 'vitest'
import type { EtatSuissePublique, RencontreSuissePublique, RondePublique } from './api'
import { enDemiPoints, formatPublicDuSuisse } from './publique'

const MARTIN = { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' }
const DURAND = { archer_id: 2, nom: 'DURAND', prenom: 'Eve' }
const PETIT = { archer_id: 3, nom: 'PETIT', prenom: 'Ana' }

function mkRencontre(over: Partial<RencontreSuissePublique> = {}): RencontreSuissePublique {
  return {
    numero: 1,
    ronde: 1,
    couloirs: null,
    haut: MARTIN,
    bas: DURAND,
    points_haut: null,
    points_bas: null,
    vainqueur: null,
    termine: false,
    validee: false,
    desynchronisee: false,
    ...over,
  }
}

function mkRonde(over: Partial<RondePublique> = {}): RondePublique {
  return { numero: 1, rencontres: [mkRencontre()], bye: null, close: false, ...over }
}

function mkEtat(over: Partial<EtatSuissePublique> = {}): EtatSuissePublique {
  return {
    phase_id: 7,
    nb_rondes: 3,
    rondes_maximales: 3,
    effectif: 3,
    rondes: [mkRonde()],
    classement: [],
    conflits: [],
    ...over,
  }
}

describe('enDemiPoints', () => {
  it('rend la moitié d’un total doublé', () => {
    expect(enDemiPoints(0)).toBe('0')
    expect(enDemiPoints(1)).toBe('½')
    expect(enDemiPoints(2)).toBe('1')
    expect(enDemiPoints(3)).toBe('1½')
    expect(enDemiPoints(4)).toBe('2')
    expect(enDemiPoints(7)).toBe('3½')
  })

  it('n’écrit pas « 0½ »', () => {
    // Le zéro entier disparaît devant la moitié : « ½ », pas « 0½ ». Détail d'écriture, mais c'est
    // la seule valeur où la règle générale (`entier` + `½`) rend un résultat qu'on n'écrit pas.
    expect(enDemiPoints(1)).toBe('½')
  })
})

describe('formatPublicDuSuisse', () => {
  it('rend un seul bloc sans titre — un suisse n’a pas de groupes', () => {
    const format = formatPublicDuSuisse(mkEtat())

    expect(format.blocs).toHaveLength(1)
    expect(format.blocs[0]?.titre).toBeNull()
  })

  it('rend toutes les rondes jouées, pas seulement la dernière', () => {
    // CA « l'historique des tours reste lisible » (cadrage du 17/08/2026) : un spectateur qui arrive
    // à la ronde 3 doit pouvoir lire les deux premières.
    const format = formatPublicDuSuisse(
      mkEtat({
        rondes: [
          mkRonde({ numero: 2, close: false }),
          mkRonde({ numero: 1, close: true }),
          mkRonde({ numero: 3, close: false }),
        ],
      }),
    )

    // Et dans l'ordre, quel que soit celui du serveur.
    expect(format.blocs[0]?.tours.map((t) => t.libelle)).toEqual(['Ronde 1', 'Ronde 2', 'Ronde 3'])
  })

  it('porte le bye sur la ronde, jamais comme une rencontre sans adversaire', () => {
    const format = formatPublicDuSuisse(mkEtat({ rondes: [mkRonde({ bye: PETIT })] }))

    expect(format.blocs[0]?.tours[0]?.exempt).toEqual(PETIT)
    // Une rencontre fantôme « PETIT vs — » se lirait comme un appariement en attente alors que
    // personne ne viendra.
    expect(format.blocs[0]?.tours[0]?.rencontres).toHaveLength(1)
  })

  it('rend le classement en points lisibles, avec les noms relevés sur les appariements', () => {
    // ⚠️ Différence structurelle avec les poules : l'état public du suisse ne porte **aucune** liste
    // de participants. Le seul endroit où un nom existe est l'appariement — c'est de là qu'il vient.
    const format = formatPublicDuSuisse(
      mkEtat({
        classement: [
          { rang: 1, archer_id: MARTIN.archer_id, points: 3, buchholz: 4, ex_aequo: false },
          { rang: 2, archer_id: DURAND.archer_id, points: 1, buchholz: 6, ex_aequo: false },
        ],
      }),
    )

    expect(format.blocs[0]?.classement).toEqual([
      { rang: 1, archer_id: 1, nom: 'Luc MARTIN', valeurs: ['1½', '2'], ex_aequo: false },
      { rang: 2, archer_id: 2, nom: 'Eve DURAND', valeurs: ['½', '3'], ex_aequo: false },
    ])
  })

  it('dit pourquoi la ronde suivante n’est pas là', () => {
    // Le moteur refuse d'apparier par-dessus une ronde en cours. Sans ce mot, le spectateur lit un
    // blanc et conclut à une panne.
    const enCours = formatPublicDuSuisse(mkEtat({ rondes: [mkRonde({ close: false })] }))
    expect(enCours.blocs[0]?.notes[0]).toContain('validées')

    const close = formatPublicDuSuisse(mkEtat({ rondes: [mkRonde({ close: true })] }))
    expect(close.blocs[0]?.notes[0]).toContain('pas encore appariée')
  })

  it('ne dit rien quand toutes les rondes prévues sont là', () => {
    const complet = formatPublicDuSuisse(
      mkEtat({
        nb_rondes: 2,
        rondes_maximales: 2,
        rondes: [mkRonde({ numero: 1, close: true }), mkRonde({ numero: 2, close: true })],
      }),
    )

    expect(complet.blocs[0]?.notes).toEqual([
      'Les 2 rondes ont été tirées : le classement ci-dessous est définitif.',
    ])
  })

  // ⚠️ **Le nombre de rondes dues est borné par l'effectif, pas par le réglage.** `nb_rondes` vaut 5
  // par défaut ; à 4 archers, le moteur n'en apparie que 3. Comparer au réglage seul affichait
  // « Ronde 3 sur 5 — l'appariement de la suivante est imminent » à perpétuité sur une phase finie.
  // La fixture posait `nb_rondes === rondes_maximales` partout, donc rien ne pouvait rougir.
  it('borne les rondes dues par rondes_maximales, jamais par le seul réglage', () => {
    const fini = formatPublicDuSuisse(
      mkEtat({
        nb_rondes: 5,
        rondes_maximales: 3,
        rondes: [
          mkRonde({ numero: 1, close: true }),
          mkRonde({ numero: 2, close: true }),
          mkRonde({ numero: 3, close: true }),
        ],
      }),
    )

    const note = fini.blocs[0]?.notes[0] ?? ''
    expect(note).not.toContain('sur 5')
    expect(note).toContain('3 rondes ont été tirées')
  })

  // ⚠️ Le serveur rend une photo **vide** sous deux participants : c'est l'état nominal du matin,
  // pas une erreur. Comme le suisse fabrique toujours un bloc, le vide générique de `VueRencontres`
  // est inatteignable ici — sans ce cas, l'écran affichait « Ronde 0 sur 5 ».
  it('ne parle pas de « ronde 0 » sur une phase encore sans participants', () => {
    const vide = formatPublicDuSuisse(mkEtat({ nb_rondes: 5, rondes_maximales: 0, rondes: [] }))

    const note = vide.blocs[0]?.notes[0] ?? ''
    expect(note).not.toContain('Ronde 0')
    expect(note).toContain('pas encore de participants')
  })

  it('ne montre jamais un code technique de conflit au spectateur', () => {
    const format = formatPublicDuSuisse(mkEtat({ conflits: [{ groupe: 1, raison: 'non_posee' }] }))

    expect(format.conflits[0]).not.toMatch(/_/)
    expect(format.conflits[0]).toContain('plan de tir')
  })
})
