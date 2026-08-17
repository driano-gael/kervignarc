// Tests de la présentation publique du **Big Shoot Off** (E05US031).
//
// Une seule règle, mais elle décide de ce qu'on lit en haut d'un écran projeté : **les finalistes
// encore en lice d'abord, puis les sortis du mieux classé au dernier**. L'ordre du serveur suit la
// composition de la phase, si bien qu'un archer éliminé à la manche 1 pouvait ouvrir le tableau
// pendant que les quatre derniers se disputaient le titre dessous.

import { describe, expect, it } from 'vitest'
import type { EtatBigShootOffPublic, TireurPublic } from './api'
import { estSorti, lignesTireurs } from './publique'

function mkTireur(over: Partial<TireurPublic> & { archer_id: number }): TireurPublic {
  return {
    nom: 'ARCHER',
    prenom: 'Un',
    en_lice: over.rang === undefined || over.rang === null,
    rang: null,
    scores: [],
    ...over,
  }
}

function mkEtat(tireurs: TireurPublic[]): EtatBigShootOffPublic {
  return {
    phase_id: 9,
    projection: {
      effectif: tireurs.length,
      eliminations: [2, 1],
      paliers: [4, 3],
      restants: tireurs.filter((t) => t.rang === null).length,
      manches_jouables: 2,
    },
    tireurs,
    manches: [],
    termine: false,
    barrage: null,
  }
}

describe('lignesTireurs', () => {
  it('met les archers en lice en tête, puis les sortis du meilleur rang au dernier', () => {
    const lignes = lignesTireurs(
      mkEtat([
        mkTireur({ archer_id: 1, nom: 'SORTI-TOT', prenom: 'A', rang: 6, en_lice: false }),
        mkTireur({ archer_id: 2, nom: 'EN-LICE', prenom: 'B' }),
        mkTireur({ archer_id: 3, nom: 'SORTI-TARD', prenom: 'C', rang: 3, en_lice: false }),
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
    const [enLice, sorti] = lignesTireurs(
      mkEtat([mkTireur({ archer_id: 1, rang: 4, en_lice: false }), mkTireur({ archer_id: 2 })]),
    )

    expect(enLice?.rang).toBeNull()
    expect(estSorti(enLice as never)).toBe(false)
    expect(sorti?.rang).toBe(4)
    expect(estSorti(sorti as never)).toBe(true)
  })

  it('recopie les scores des manches validées sans les compléter', () => {
    // `scores` ne porte que les manches **entièrement validées**. Les rembourrer d'un zéro ferait
    // lire « 0 » là où il n'y a pas encore de résultat, et un spectateur croirait l'archer effondré.
    const [ligne] = lignesTireurs(mkEtat([mkTireur({ archer_id: 1, scores: [27] })]))

    expect(ligne?.scores).toEqual([27])
  })
})
