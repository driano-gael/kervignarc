import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import { MARQUEURS_DE_DOM, TESTS_TS_AVEC_DOM } from './test-environnement'

const modulesTs = readdirSync('src', { recursive: true, encoding: 'utf-8' })
  .filter((chemin) => chemin.endsWith('.test.ts'))
  .map((chemin) => join('src', chemin).replaceAll('\\', '/'))

const aBesoinDuDom = (chemin: string) => MARQUEURS_DE_DOM.test(readFileSync(chemin, 'utf-8'))

describe('répartition des tests entre les projets Vitest', () => {
  it('trouve bien les modules `.test.ts` — sinon ce garde-fou ne vérifie rien', () => {
    expect(modulesTs.length).toBeGreaterThan(50)
  })

  it('ne laisse aucun module hors liste réclamer un DOM', () => {
    const horsListe = modulesTs.filter(
      (chemin) => !TESTS_TS_AVEC_DOM.includes(chemin) && aBesoinDuDom(chemin),
    )
    expect(horsListe).toEqual([])
  })

  it('ne garde dans la liste que des modules existants', () => {
    const absents = TESTS_TS_AVEC_DOM.filter((chemin) => !modulesTs.includes(chemin))
    expect(absents).toEqual([])
  })

  it('ne garde dans la liste aucun module qui se passerait de jsdom', () => {
    const inutiles = TESTS_TS_AVEC_DOM.filter((chemin) => !aBesoinDuDom(chemin))
    expect(inutiles).toEqual([])
  })
})
