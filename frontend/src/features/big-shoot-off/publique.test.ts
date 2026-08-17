// Tests de la présentation publique du **Big Shoot Off** (E05US031).
//
// Une seule règle, mais elle décide de ce qu'on lit en haut d'un écran projeté : **les finalistes
// encore en lice d'abord, puis les sortis du mieux classé au dernier**. L'ordre du serveur suit la
// composition de la phase, si bien qu'un archer éliminé à la manche 1 pouvait ouvrir le tableau
// pendant que les quatre derniers se disputaient le titre dessous.

import { describe, expect, it } from 'vitest'
import type { EtatBigShootOffPublic, TireurPublic } from './api'
import { estAchevee, estSorti, libelleSort, lignesTireurs, nbEnLice } from './publique'

/** ⚠️ **Plus de champ `en_lice`** : il a quitté le contrat public en revue. La fixture le
 * **calculait depuis `rang`**, ce qui rendait leur divergence infalsifiable par construction — le
 * jour où sortir de la lice cesserait de décerner un rang (forfait, disqualification), aucun test
 * n'aurait rougi. Un seul champ porte le fait, `rang`. */
function mkTireur(over: Partial<TireurPublic> & { archer_id: number }): TireurPublic {
  return {
    nom: 'ARCHER',
    prenom: 'Un',
    rang: null,
    scores: [],
    ...over,
  }
}

/** ⚠️ **La projection est DÉRIVÉE de l'effectif, jamais posée en dur.** Le serveur ne produit que
 * des paliers strictement inférieurs à l'effectif (`paliers_pour`), et `restants` vaut toujours
 * `paliers[-1]` : une fixture qui l'ignore invite à raisonner faux — c'est ainsi qu'est né le
 * défaut bloquant de la 1ʳᵉ passe (`paliers:[1]` avec `restants:2`), et la 2ᵉ passe a trouvé que
 * cette fixture-ci le rejouait en plus petit (`paliers:[4,3]` sur deux ou trois tireurs).
 *
 * `manches` porte une entrée : c'est ce qui distingue une phase **achevée** d'une phase `termine`
 * qui n'a jamais commencé (population vide, ou réglage injouable). */
function mkEtat(
  tireurs: TireurPublic[],
  over: Partial<EtatBigShootOffPublic> = {},
): EtatBigShootOffPublic {
  const fin = Math.max(1, tireurs.length - 1)
  return {
    phase_id: 9,
    projection: { effectif: tireurs.length, paliers: [fin], restants: fin },
    tireurs,
    manches: [
      { numero: 1, elimine: Math.max(0, tireurs.length - fin), complete: true, jouee: true },
    ],
    termine: false,
    barrage: null,
    ...over,
  }
}

describe('lignesTireurs', () => {
  it('met les archers en lice en tête, puis les sortis du meilleur rang au dernier', () => {
    const lignes = lignesTireurs(
      mkEtat([
        mkTireur({ archer_id: 1, nom: 'SORTI-TOT', prenom: 'A', rang: 6 }),
        mkTireur({ archer_id: 2, nom: 'EN-LICE', prenom: 'B' }),
        mkTireur({ archer_id: 3, nom: 'SORTI-TARD', prenom: 'C', rang: 3 }),
      ]),
    )

    // Le Big Shoot Off élimine par le bas : le **dernier** sorti porte le plus petit rang. Trier par
    // ordre de sortie mettrait le 6ᵉ devant le 3ᵉ — l'inverse de ce qu'on vient chercher.
    expect(lignes.map((l) => l.archer_id)).toEqual([2, 3, 1])
  })

  it('départage deux archers en lice par NOM puis prénom, jamais par prénom', () => {
    // Deux raisons, et la seconde est un défaut trouvé par ce test même :
    //  - sans clé de départage, l'ordre des ex æquo suivait celui du serveur : deux lectures
    //    successives pouvaient permuter deux lignes sur un écran projeté, ce qui se lit comme un
    //    changement de classement ;
    //  - la première version triait la chaîne **rédigée** (« Prénom NOM »), donc par prénom. Une
    //    liste d'archers se lit par nom de famille, et l'écart ne se voit que sur des noms choisis
    //    exprès — d'où ces deux-là.
    const lignes = lignesTireurs(
      mkEtat([
        mkTireur({ archer_id: 1, nom: 'ZULU', prenom: 'Anne' }),
        mkTireur({ archer_id: 2, nom: 'ALPHA', prenom: 'Bob' }),
        mkTireur({ archer_id: 3, nom: 'ALPHA', prenom: 'Ada' }),
      ]),
    )

    expect(lignes.map((l) => l.nom)).toEqual(['Ada ALPHA', 'Bob ALPHA', 'Anne ZULU'])
  })

  it('retient le rang, qui porte aussi la place obtenue', () => {
    const lignes = lignesTireurs(
      mkEtat([mkTireur({ archer_id: 1, rang: 4 }), mkTireur({ archer_id: 2 })]),
    )

    // Assertion sur la **liste**, pas sur deux éléments déstructurés : cela supprime le `as never`
    // qui neutralisait le typage pour contourner un `| undefined`, et verrouille l'ordre au passage.
    expect(lignes.map((l) => l.rang)).toEqual([null, 4])
    expect(lignes.map(estSorti)).toEqual([false, true])
  })

  it('recopie les scores des manches validées sans les compléter', () => {
    // `scores` ne porte que les manches **entièrement validées**. Les rembourrer d'un zéro ferait
    // lire « 0 » là où il n'y a pas encore de résultat, et un spectateur croirait l'archer effondré.
    const [ligne] = lignesTireurs(mkEtat([mkTireur({ archer_id: 1, scores: [27] })]))

    expect(ligne?.scores).toEqual([27])
  })
})

describe('nbEnLice', () => {
  // ⚠️ **Le défaut bloquant de cette US.** L'écran affichait `projection.restants`, qui vaut
  // `paliers[-1]` — l'effectif **à la fin** du format, une constante connue avant le premier tir.
  // Sur une finale 12 → 8 → 6 → 5 il annonçait « 5 archers en lice » dès la manche 1 ; sur le cas
  // nominal (déroulé validé à 1 rescapé), « 1 archer en lice » du début à la fin.
  it('compte les archers qui tirent ENCORE, pas l’effectif de fin de format', () => {
    // Échelle annoncée : 3 au départ, la phase se terminera à 1 — et deux archers tirent encore.
    // Les deux nombres doivent différer, sinon le test passerait aussi avec `projection.restants`.
    const etat = mkEtat(
      [mkTireur({ archer_id: 1 }), mkTireur({ archer_id: 2 }), mkTireur({ archer_id: 3, rang: 3 })],
      { projection: { effectif: 3, paliers: [2, 1], restants: 1 } },
    )

    expect(etat.projection.restants).toBe(1)
    expect(nbEnLice(etat)).toBe(2)
  })

  it('rend 0 sur une phase encore sans population', () => {
    expect(nbEnLice(mkEtat([]))).toBe(0)
  })
})

describe('libelleSort', () => {
  it('dit « en lice » tant que la phase se joue', () => {
    const etat = mkEtat([mkTireur({ archer_id: 1 })])
    const [ligne] = lignesTireurs(etat)

    expect(libelleSort(ligne!, etat)).toBe('En lice')
  })

  it('nomme le rang d’un archer sorti', () => {
    const etat = mkEtat([mkTireur({ archer_id: 1, rang: 4 })])
    const [ligne] = lignesTireurs(etat)

    expect(libelleSort(ligne!, etat)).toBe('4ᵉ')
  })

  // ⚠️ **Le rescapé n'a pas de rang** : le serveur ne range que les éliminés. Sans le cas
  // `termine`, le vainqueur de la finale restait affiché « En lice » jusqu'au soir, alors que le
  // palmarès le donne 1ᵉʳ.
  it('nomme le vainqueur une fois la finale terminée', () => {
    const etat = mkEtat([mkTireur({ archer_id: 1 }), mkTireur({ archer_id: 2, rang: 2 })], {
      termine: true,
    })
    const lignes = lignesTireurs(etat)

    expect(lignes.map((l) => libelleSort(l, etat))).toEqual(['Vainqueur', '2ᵉ'])
  })

  // ⚠️ **« 1ᵉʳ ex æquo », et surtout pas « Qualifié »** (correction de la 2ᵉ passe de revue) : le
  // domaine donne le rang 1 **partagé** aux restants (`EtatBigShootOff.classement` — « la règle ne
  // prévoit rien pour les départager entre eux »). « Qualifié » faisait dire deux choses
  // différentes des mêmes archers à cet onglet et au palmarès, et promettait une phase suivante que
  // le front ne peut pas connaître.
  it('dit « 1ᵉʳ ex æquo » quand l’échelle s’arrête à plusieurs rescapés', () => {
    const etat = mkEtat(
      [mkTireur({ archer_id: 1 }), mkTireur({ archer_id: 2 }), mkTireur({ archer_id: 3, rang: 3 })],
      { termine: true },
    )
    const lignes = lignesTireurs(etat)

    expect(lignes.map((l) => libelleSort(l, etat))).toEqual(['1ᵉʳ ex æquo', '1ᵉʳ ex æquo', '3ᵉ'])
  })

  // ⚠️ Deux états où `termine` est vrai **avant le premier tir** : population vide, et réglage
  // injouable (une liste de sortants qui ne laisserait personne). `manches` est vide dans les deux.
  it('ne déclare achevée ni une phase vide ni un réglage injouable', () => {
    const vide = mkEtat([], { termine: true, manches: [] })
    expect(estAchevee(vide)).toBe(false)

    const injouable = mkEtat([mkTireur({ archer_id: 1 }), mkTireur({ archer_id: 2 })], {
      termine: true,
      manches: [],
    })
    expect(estAchevee(injouable)).toBe(false)
    // ...donc personne n'y est annoncé « 1ᵉʳ ex æquo » sans avoir tiré une flèche.
    expect(lignesTireurs(injouable).map((l) => libelleSort(l, injouable))).toEqual([
      'En lice',
      'En lice',
    ])
  })
})
