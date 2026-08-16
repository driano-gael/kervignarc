// Ce que l'écran du système suisse dit — logique pure, aucun DOM (E05US030).
//
// ⚠️ **Ce fichier est né d'une revue**, et le manque qu'il comble mérite d'être nommé : les trois
// fonctions ci-dessous vivaient dans `SaisieSuisse.tsx`, donc n'étaient testables par rien. Deux
// d'entre elles portent un CA de l'US — la conversion des points en victoires et la phrase qui
// explique pourquoi la ronde suivante n'est pas là —, et la fiche de recette désignait la première
// comme « à vérifier à la main ». Une erreur de facteur 2 y est **silencieuse** : « 6 » au lieu de
// « 3 » reste un classement parfaitement plausible.

import { describe, expect, it } from 'vitest'

import {
  decrirePlaces,
  decrirePoints,
  etatRencontre,
  motDeLaFin,
  nomDeLArcher,
  type RondeLisible,
} from './presentation'

function duelliste(archerId: number) {
  return { archer_id: archerId, nom: `NOM${archerId}`, prenom: `Prenom${archerId}` }
}

function ronde(numero: number, close: boolean, patch: Partial<RondeLisible> = {}): RondeLisible {
  return {
    numero,
    close,
    bye: null,
    rencontres: [{ haut: duelliste(1), bas: duelliste(2) }],
    ...patch,
  }
}

describe('decrirePoints', () => {
  it('rend des VICTOIRES, pas les demi-points doublés du serveur', () => {
    // Le serveur compte une victoire 2 et un nul 1, pour ne comparer que des entiers.
    expect(decrirePoints(0)).toBe('0')
    expect(decrirePoints(2)).toBe('1')
    expect(decrirePoints(4)).toBe('2')
    expect(decrirePoints(6)).toBe('3')
  })

  it('rend la demie sur un total impair', () => {
    expect(decrirePoints(1)).toBe('0,5')
    expect(decrirePoints(3)).toBe('1,5')
    expect(decrirePoints(5)).toBe('2,5')
    expect(decrirePoints(13)).toBe('6,5')
  })
})

describe('motDeLaFin', () => {
  it('nomme l’attente quand la ronde en cours n’est pas close et qu’il en reste', () => {
    // Le CA : « la ronde suivante n'apparaît qu'une fois la précédente close, et l'écran le dit ».
    expect(motDeLaFin([ronde(1, false)], 3)).toEqual({
      etat: 'attente',
      courante: 1,
      suivante: 2,
    })
  })

  it('annonce la fin quand toutes les rondes dues sont closes', () => {
    expect(motDeLaFin([ronde(1, true), ronde(2, true)], 2)).toEqual({ etat: 'fini' })
  })

  it('SE TAIT quand la dernière ronde due est en cours', () => {
    // Le cas que personne ne gardait : il n'y a pas de ronde suivante à promettre (on est à la
    // dernière), et rien n'est terminé non plus. Les deux messages seraient faux.
    expect(motDeLaFin([ronde(1, true), ronde(2, false)], 2)).toBeNull()
  })

  it('se tait sur une phase sans ronde, ou dont l’effectif n’en permet aucune', () => {
    // `rondesDues === 0` arrive dès que l'effectif est inférieur à deux : le serveur rend alors
    // `rondes_maximales = 0`. Annoncer « toutes les rondes sont jouées » y serait absurde.
    expect(motDeLaFin([], 3)).toBeNull()
    expect(motDeLaFin([], 0)).toBeNull()
    expect(motDeLaFin([ronde(1, true)], 0)).toBeNull()
  })

  it('ne promet pas une ronde de plus que ce que l’effectif permet', () => {
    // 5 rondes réglées mais 3 permises : à la 3ᵉ close, c'est fini — même si `nb_rondes` dit 5.
    expect(motDeLaFin([ronde(1, true), ronde(2, true), ronde(3, true)], 3)).toEqual({
      etat: 'fini',
    })
  })
})

describe('nomDeLArcher', () => {
  it('retrouve un archer par ses rencontres', () => {
    expect(nomDeLArcher([ronde(1, true)], 2)).toBe('NOM2 Prenom2')
  })

  it('retrouve le porteur du bye, qui ne figure dans aucune rencontre', () => {
    // À effectif impair il chôme : sans ce cas, il s'afficherait « #3 » au classement — alors que
    // son repos lui compte une victoire et qu'il y est donc bien classé.
    const impaire = ronde(1, true, { bye: duelliste(3) })
    expect(nomDeLArcher([impaire], 3)).toBe('NOM3 Prenom3')
  })

  it('retombe sur l’identifiant plutôt que sur du vide', () => {
    expect(nomDeLArcher([ronde(1, true)], 99)).toBe('#99')
  })
})

describe('decrirePlaces', () => {
  // ⚠️ Extraite pour être testable, elle ne l'était pas encore (relevé au 2ᵉ tour). Elle est
  // maintenant lue sur la **ligne de rencontre** : c'est ce que le scoreur suit pour aller à la
  // butte.
  it('groupe les couloirs par cible', () => {
    expect(
      decrirePlaces([
        [1, 'A'],
        [1, 'B'],
      ]),
    ).toBe('cible 1 : A, B')
  })

  it('nomme les DEUX cibles quand la rencontre est à cheval', () => {
    // Un bloc est contigu dans la salle *mise à plat*, pas sur une seule cible : c'est le cas
    // nominal dès qu'une phase ne tombe pas pile sur une butte.
    expect(
      decrirePlaces([
        [1, 'D'],
        [2, 'A'],
      ]),
    ).toBe('cible 1 : D · cible 2 : A')
  })
})

describe('etatRencontre', () => {
  // ⚠️ Le `duel` est fusionné **après** le reste du patch : l'écraser en bloc ferait passer
  // `validee_par` à `undefined`, donc `!== null`, et toute rencontre s'annoncerait « validée ».
  // C'est arrivé au premier jet de ce fichier — le test a rougi, ce qui est exactement son travail.
  function rencontre(patch: { desynchronisee?: boolean; duel?: Record<string, unknown> } = {}) {
    return {
      numero: 1,
      ronde: 1,
      couloirs: null,
      haut: duelliste(1),
      bas: duelliste(2),
      desynchronisee: patch.desynchronisee ?? false,
      duel: {
        validee_par: null,
        validation_en_attente: false,
        resultat: null,
        manches: [],
        ...(patch.duel ?? {}),
      },
    } as unknown as Parameters<typeof etatRencontre>[0]
  }

  it('annonce « à tirer » sur une rencontre vierge', () => {
    expect(etatRencontre(rencontre())).toBe('à tirer')
  })

  it('suit l’avancement du duel, dans l’ordre', () => {
    expect(etatRencontre(rencontre({ duel: { manches: [{}] } }))).toBe('en cours')
    expect(etatRencontre(rencontre({ duel: { resultat: { termine: true } } }))).toBe('à valider')
    expect(etatRencontre(rencontre({ duel: { validation_en_attente: true } }))).toBe(
      'validation en attente',
    )
    expect(etatRencontre(rencontre({ duel: { validee_par: 'Camille' } }))).toBe('validée')
  })

  it('fait passer la DÉSYNCHRONISATION avant tout le reste', () => {
    // L'ordre compte : une rencontre désynchronisée dont le duel est par ailleurs validé ne doit
    // pas s'annoncer « validée » — c'est ce libellé qui explique pourquoi la ligne est bloquée.
    const bloquee = rencontre({ desynchronisee: true, duel: { validee_par: 'Camille' } })
    expect(etatRencontre(bloquee)).toBe('tir mis de côté — population à rétablir')
  })
})
