// Tests de la plomberie de navigation (E14US003, ADR-0059).
//
// Un seul comportement mérite vraiment un test ici, mais il est **critique le jour J** : la navigation
// doit **conserver la query**. Les QR imprimés (E09US008) pointent vers `/?poste=<CODE>` ; l'app
// corrige l'adresse vers `/cible` au montage (verrou `D-13`). Si cette correction perdait le
// paramètre, toutes les étiquettes déjà collées devant les cibles deviendraient muettes.

import { beforeEach, describe, expect, it } from 'vitest'
import { naviguer } from './useChemin'

describe('naviguer', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/')
  })

  it('change le chemin', () => {
    naviguer('/admin/pilotage/supervision')
    expect(window.location.pathname).toBe('/admin/pilotage/supervision')
  })

  it('CONSERVE la query — les QR déjà imprimés doivent survivre', () => {
    window.history.replaceState(null, '', '/?poste=A7X9')
    naviguer('/cible', { remplacer: true })
    expect(window.location.pathname).toBe('/cible')
    expect(new URLSearchParams(window.location.search).get('poste')).toBe('A7X9')
  })

  it('« remplacer » n’empile pas d’entrée d’historique', () => {
    const avant = window.history.length
    naviguer('/public', { remplacer: true })
    expect(window.history.length).toBe(avant)
  })

  it('naviguer vers l’adresse courante ne fait rien', () => {
    naviguer('/public')
    const apres = window.history.length
    naviguer('/public')
    expect(window.history.length).toBe(apres)
  })
})
