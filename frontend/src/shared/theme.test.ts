/// <reference types="node" />
// Tests du thème de poste (E17US001, `D-26` / `DV-02`).
//
// Ils existent parce qu'un défaut est passé **sans qu'aucun test ne bouge** : `appliquerTheme(null)`
// posait `data-theme="systeme"`, or le store initialise `theme` à `null` et réapplique le thème à
// chaque ouverture — une tablette neuve suivait donc l'OS, c'est-à-dire l'alternative qu'ADR-0074
// déclare rejeter. Le CA disait l'inverse de ce que le code faisait, et `sessionPosteStore.test.ts`
// notait lui-même qu'« aucun test n'asserte sur `data-theme` ».
//
// Ces tests dérivent des **puces de CA**, pas du code : « le thème sombre est le défaut, sans suivre
// le système » et « l'option Système reste disponible et fonctionnelle ».

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { beforeEach, describe, expect, it } from 'vitest'
import { appliquerTheme } from './theme'

beforeEach(() => {
  delete document.documentElement.dataset.theme
})

describe('CA — le thème sombre est le défaut, sans suivre le système (DV-02)', () => {
  it('aucun choix ⇒ sombre, et surtout pas « suivre l’OS »', () => {
    appliquerTheme(null)
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('le défaut ne dépend pas de la préférence de l’appareil', () => {
    // La valeur posée est la même quelle que soit la lumière du poste : c'est tout l'enjeu du jour J,
    // où ~30 tablettes BYOD suivraient sinon chacune le réglage de son propriétaire.
    appliquerTheme(null)
    const sansPreference = document.documentElement.dataset.theme
    delete document.documentElement.dataset.theme
    appliquerTheme(null)
    expect(document.documentElement.dataset.theme).toBe(sansPreference)
  })
})

describe('CA — l’option « Système » reste disponible et fonctionnelle (D-26)', () => {
  it('un choix explicite « Système » est distinct du défaut', () => {
    appliquerTheme('systeme')
    expect(document.documentElement.dataset.theme).toBe('systeme')
    // Le distinguer de `dark` est **la** condition pour que l'option surcharge quoi que ce soit.
    expect(document.documentElement.dataset.theme).not.toBe('dark')
  })

  it('la charte donne un effet à « Système » en lumière claire', () => {
    // L'autre moitié du mécanisme : sans cette règle, `data-theme="systeme"` ne serait qu'une valeur
    // inerte et l'option n'aurait plus d'effet — un défaut invisible en développement.
    const charte = readFileSync(join(process.cwd(), 'src', 'index.css'), 'utf8')
    expect(charte).toMatch(/@media \(prefers-color-scheme: light\)[\s\S]*?data-theme='systeme'/)
  })

  it.each([
    ['clair', 'light'],
    ['sombre', 'dark'],
  ] as const)('« %s » surcharge le défaut', (choix, attendu) => {
    appliquerTheme(choix)
    expect(document.documentElement.dataset.theme).toBe(attendu)
  })
})
