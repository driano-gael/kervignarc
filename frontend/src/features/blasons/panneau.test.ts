// A06 · référentiels — variante retenue au questionnaire du 04/08 : « B — Panneau latéral
// d'édition » (« on voit rapidement ce qui compose une ligne par sélection »), avec la réserve
// « séparer visuellement les unités officielles FFTA de celles créées par l'admin ». E17US007.

import { describe, expect, it } from 'vitest'
import type { Blason } from './api'
import { groupesParOrigine, selectionCourante } from './panneau'

const blason = (id: number, origine: Blason['origine']): Blason => ({
  id,
  tournoi_id: 1,
  nom: `Blason ${id}`,
  taille: 1,
  capacite: 1,
  zones: ['10', 'M'],
  origine,
})

describe('groupesParOrigine', () => {
  it('le référentiel FFTA d’abord, les créations de l’organisation ensuite', () => {
    const groupes = groupesParOrigine([blason(1, 'utilisateur'), blason(2, 'ffta')])
    expect(groupes.map((g) => g.origine)).toEqual(['ffta', 'utilisateur'])
    expect(groupes[0]?.blasons.map((b) => b.id)).toEqual([2])
  })

  it('un groupe vide n’est pas rendu — pas de titre au-dessus de rien', () => {
    expect(groupesParOrigine([blason(1, 'ffta')]).map((g) => g.origine)).toEqual(['ffta'])
  })
})

describe('selectionCourante', () => {
  it('le blason choisi, relu dans la liste courante', () => {
    const liste = [blason(1, 'ffta'), blason(2, 'utilisateur')]
    expect(selectionCourante({ mode: 'edition', id: 2 }, liste)).toEqual({
      mode: 'edition',
      blason: liste[1],
    })
  })

  it('un blason disparu (supprimé) ferme le panneau au lieu d’éditer un fantôme', () => {
    expect(selectionCourante({ mode: 'edition', id: 9 }, [blason(1, 'ffta')])).toBeNull()
  })

  it('la création ne dépend d’aucune ligne', () => {
    expect(selectionCourante({ mode: 'creation' }, [])).toEqual({ mode: 'creation' })
  })
})
