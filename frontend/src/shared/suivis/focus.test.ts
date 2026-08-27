// Tests de la bascule « mes archers / tout » (E16US004), **dérivés du CA** — écrits avant le
// câblage des écrans (règle 9).
//
// Source : `stories/E16-retours-maquettes.md` § E16US004, puce « CA — bascule mes archers / tout »,
// élargie au cadrage du 08/08/2026 à **tout l'onglet public** (un interrupteur unique en tête
// d'écran plutôt qu'un par vue). Questionnaires derrière le CA : P03 et P05.

import { describe, expect, it } from 'vitest'
import type { ArcherSuivi } from '../stores/sessionSuivisStore'
import { centrerCibles, centrerLignes, modeEffectif, suivisDuTournoi } from './focus'

const suivi = (archerId: number, tournoiId: number): ArcherSuivi => ({ archerId, tournoiId })

// Une ligne minimale : le seul champ que la bascule regarde est `archer_id`. Classement, palmarès et
// affectations le portent tous — c'est ce qui permet une règle unique plutôt qu'une par écran.
const ligne = (archerId: number, rang: number) => ({ archer_id: archerId, rang })

const cible = (index: number, archerIds: number[]) => ({
  index,
  placements: archerIds.map((archer_id) => ({ archer_id })),
})

describe('suivisDuTournoi', () => {
  it('ne retient que les archers suivis sur le tournoi affiché', () => {
    // Plusieurs tournois EN_COURS en parallèle est une capacité voulue (intérieur + extérieur) : le
    // store mémorise les suivis de tous, la vue ne doit compter que ceux d'ici.
    const suivis = [suivi(10, 1), suivi(20, 2), suivi(30, 1)]
    expect(suivisDuTournoi(suivis, 1)).toEqual([10, 30])
  })

  it('rend une liste vide quand rien n’est suivi ici', () => {
    expect(suivisDuTournoi([suivi(20, 2)], 1)).toEqual([])
  })
})

describe('modeEffectif', () => {
  it('rend « tout » quand la bascule est sur « tout »', () => {
    expect(modeEffectif(false, [10])).toBe('tout')
  })

  it('rend « suivis » quand la bascule est armée et qu’au moins un archer est suivi', () => {
    expect(modeEffectif(true, [10])).toBe('suivis')
  })

  it('retombe sur « tout » si aucun archer n’est suivi sur ce tournoi', () => {
    // Garde-fou : la bascule est mémorisée globalement, les suivis sont par tournoi. Sans cette
    // règle, ouvrir un tournoi où l'on ne suit personne viderait *tous* les écrans publics d'un
    // coup, sans que rien à l'écran n'explique pourquoi.
    expect(modeEffectif(true, [])).toBe('tout')
  })
})

describe('centrerLignes', () => {
  const lignes = [ligne(10, 1), ligne(20, 2), ligne(30, 3), ligne(40, 4)]

  it('ne touche à rien en mode « tout »', () => {
    expect(centrerLignes(lignes, 'tout', [20])).toEqual(lignes)
  })

  it('ne garde que les archers suivis en mode « suivis »', () => {
    expect(centrerLignes(lignes, 'suivis', [30, 10])).toEqual([ligne(10, 1), ligne(30, 3)])
  })

  it('conserve les rangs du classement complet', () => {
    // Même principe que le filtre par catégorie déjà livré (E06US001) : on **voit** une sélection
    // sans perdre la position d'ensemble. Renuméroter donnerait à l'archer suivi un « 1ᵉʳ » faux.
    expect(centrerLignes(lignes, 'suivis', [30]).map((l) => l.rang)).toEqual([3])
  })

  it('garde l’ordre de la liste source, pas celui des suivis', () => {
    expect(centrerLignes(lignes, 'suivis', [40, 10]).map((l) => l.archer_id)).toEqual([10, 40])
  })

  it('ignore un archer suivi absent de la liste', () => {
    // Suivi puis retiré du tournoi, ou pas encore classé : il ne fabrique pas de ligne fantôme.
    expect(centrerLignes(lignes, 'suivis', [99])).toEqual([])
  })
})

describe('centrerCibles', () => {
  const cibles = [cible(1, [10, 11]), cible(2, [20]), cible(3, [])]

  it('ne touche à rien en mode « tout »', () => {
    expect(centrerCibles(cibles, 'tout', [20])).toEqual(cibles)
  })

  it('ne garde que les cibles où tire au moins un archer suivi', () => {
    // Sur le plan de salle, « mes archers » veut dire « la butte où ils sont », voisins compris :
    // on filtre la **cible**, pas les places — c'est la cible entière qu'on va chercher des yeux.
    expect(centrerCibles(cibles, 'suivis', [11])).toEqual([cible(1, [10, 11])])
  })

  it('rend une liste vide si aucun archer suivi n’est encore placé', () => {
    expect(centrerCibles(cibles, 'suivis', [99])).toEqual([])
  })
})
