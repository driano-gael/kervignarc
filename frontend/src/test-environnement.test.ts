import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import {
  CHEMINS_AVEC_DOM,
  MARQUEURS_DE_DOM,
  TESTS_TS_AVEC_DOM,
  sansCommentaires,
} from './test-environnement'

// ⚠️ Doit rester le miroir exact des `include` des deux projets de `vite.config.ts` : c'est ce
// couple qui décide qu'un fichier de test est joué. Tout ce qui ressemble à un test sans y
// correspondre n'est exécuté par **aucun** projet, et Vitest ne le signale pas.
const COUVERT_PAR_UN_PROJET = /^src\/.+\.test\.tsx?$/
const RESSEMBLE_A_UN_TEST = /\.(test|spec)\.(c|m)?[jt]sx?$/

const fichiersDe = (racine: string) =>
  readdirSync(racine, { recursive: true, encoding: 'utf-8' }).map((chemin) =>
    chemin.replaceAll('\\', '/'),
  )

const modulesTs = fichiersDe('src')
  .filter((chemin) => chemin.endsWith('.test.ts'))
  .map((chemin) => join('src', chemin).replaceAll('\\', '/'))

const usageDirectDuDom = (chemin: string) =>
  MARQUEURS_DE_DOM.test(sansCommentaires(readFileSync(chemin, 'utf-8')))

describe('répartition des tests entre les projets Vitest', () => {
  it('trouve bien les modules `.test.ts` — sinon ce garde-fou ne vérifie rien', () => {
    expect(modulesTs.length).toBeGreaterThan(50)
  })

  it("n'accepte aucun fichier de test hors des deux projets", () => {
    const orphelins = fichiersDe('.')
      .filter((c) => !c.startsWith('node_modules/') && !c.startsWith('dist/'))
      .filter((c) => RESSEMBLE_A_UN_TEST.test(c))
      .filter((c) => !COUVERT_PAR_UN_PROJET.test(c))
    expect(orphelins).toEqual([])
  })

  it('ne laisse aucun module hors table réclamer un DOM', () => {
    const horsTable = modulesTs.filter(
      (chemin) => !CHEMINS_AVEC_DOM.includes(chemin) && usageDirectDuDom(chemin),
    )
    expect(horsTable).toEqual([])
  })

  it('ne garde dans la table que des modules existants', () => {
    expect(CHEMINS_AVEC_DOM.filter((chemin) => !modulesTs.includes(chemin))).toEqual([])
  })

  it('exige une raison pour chaque entrée de la table', () => {
    const sansRaison = Object.entries(TESTS_TS_AVEC_DOM)
      .filter(([, raison]) => raison.trim().length < 10)
      .map(([chemin]) => chemin)
    expect(sansRaison).toEqual([])
  })
})
