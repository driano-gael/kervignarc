// Ce que l'écran du système suisse dit — logique pure, aucun DOM (E05US030).
//
// ⚠️ **Ce fichier est né d'une revue**, et le manque qu'il comble mérite d'être nommé : les trois
// fonctions ci-dessous vivaient dans `SaisieSuisse.tsx`, donc n'étaient testables par rien. Deux
// d'entre elles portent un CA de l'US — la conversion des points en victoires et la phrase qui
// explique pourquoi la ronde suivante n'est pas là —, et la fiche de recette désignait la première
// comme « à vérifier à la main ». Une erreur de facteur 2 y est **silencieuse** : « 6 » au lieu de
// « 3 » reste un classement parfaitement plausible.

import { describe, expect, it } from 'vitest'

import type { Duel, Duelliste } from '../saisie-duels/api'
import type { RencontreSuisse } from './api'
import {
  ceQuiManque,
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

describe('ceQuiManque — le refus circonstancié (E05US034)', () => {
  // Tests écrits **depuis le CA** : *« un refus dit ce qui manque : quelles rencontres ne sont pas
  // validées, et lesquelles ne sont pas encore saisies »* (stories/E05-moteur-phases.md § E05US034,
  // CA récupéré de l'ancienne E05US032).
  //
  // ⚠️ L'oracle **n'est pas** le message existant. Celui-ci comptait — « la ronde en cours n'est pas
  // entièrement saisie » — ce qui est vrai et inutilisable dans un gymnase où quatorze rencontres se
  // jouent en parallèle. Le CA demande des **noms**, et la distinction entre deux attentes qui
  // n'appellent pas le même geste.

  function duelliste(nom: string): Duelliste {
    return { archer_id: nom.length, nom, prenom: 'X', club: null, categorie: null } as Duelliste
  }

  function rencontre(nom: string, duel: Partial<Duel>, desynchronisee = false): RencontreSuisse {
    return {
      numero: 1,
      ronde: 1,
      couloirs: null,
      haut: duelliste(nom),
      bas: duelliste('Adverse'),
      desynchronisee,
      duel: { validee_par: null, manches: [], resultat: null, ...duel } as Duel,
    } as RencontreSuisse
  }

  it('sépare ce qui attend une saisie de ce qui attend une validation', () => {
    // La distinction décide **de qui doit agir** : le scoreur de la cible, ou l'organisateur.
    const manque = ceQuiManque([
      rencontre('Pastir', {}),
      rencontre('Avalider', { resultat: { termine: true } as Duel['resultat'] }),
    ])

    expect(manque.aSaisir).toEqual(['Pastir X – Adverse X'])
    expect(manque.aValider).toEqual(['Avalider X – Adverse X'])
  })

  it('ne réclame rien d’une rencontre déjà validée', () => {
    const manque = ceQuiManque([rencontre('Finie', { validee_par: 'Camille' })])

    expect(manque).toEqual({ aSaisir: [], aValider: [], enFile: [], bloquees: [] })
  })

  it('range à part une validation posée mais restée en file hors-ligne', () => {
    // ⚠️ Arbitrage de revue (E05US034) : `etatRencontre` distingue « validation en attente »
    // (E04US009) ; sans ce cas, la même rencontre s'annonçait « validation en attente » dans la
    // liste et « il manque une validation » dans le résumé. Ce résumé répond à **qui aller
    // chercher** : une validation en file ne demande personne, elle attend le réseau.
    const manque = ceQuiManque([
      rencontre('Enfile', {
        resultat: { termine: true } as Duel['resultat'],
        validation_en_attente: true,
      }),
    ])

    expect(manque.aValider).toEqual([])
    // ⚠️ **Nommée, pas écartée** (correction de 2ᵉ passe). L'écarter rendait le résumé **vide** sous
    // la phrase « la ronde suivante sera appariée quand celle-ci sera saisie et validée » : plus
    // rien n'expliquait l'attente, soit le cul-de-sac que ce CA ferme. Et `validation_en_attente`
    // est purement **local** — l'organisateur ne le voit jamais, donc « ça n'appelle personne » ne
    // justifiait pas de le taire.
    expect(manque.enFile).toEqual(['Enfile X – Adverse X'])
  })

  it('compte une rencontre à demi tirée comme « à saisir », pas « à valider »', () => {
    // ⚠️ Le piège : `manches.length > 0` ferait passer une rencontre en cours pour finie, donc
    // enverrait chercher une validation que personne ne peut donner. C'est `resultat.termine` qui
    // tranche — la même lecture qu'`etatRencontre`, pour que deux phrases du même écran s'accordent.
    const manque = ceQuiManque([
      rencontre('Encours', {
        manches: [{}] as Duel['manches'],
        resultat: { termine: false } as Duel['resultat'],
      }),
    ])

    expect(manque.aSaisir).toEqual(['Encours X – Adverse X'])
    expect(manque.aValider).toEqual([])
  })

  it('range à part une rencontre désynchronisée', () => {
    // Elle n'attend ni saisie ni validation mais un rétablissement de population (ADR-0049 §4) :
    // l'annoncer « à saisir » enverrait le scoreur buter sur un tir que le serveur refuse d'écraser.
    const manque = ceQuiManque([rencontre('Bloquee', {}, true)])

    expect(manque.bloquees).toEqual(['Bloquee X – Adverse X'])
    expect(manque.aSaisir).toEqual([])
  })
})
