/// <reference types="node" />

// Tests du thème de poste (E17US001, `D-26` / `DV-02`).
//
// Ils existent parce qu'un défaut est passé **sans qu'aucun test ne bouge** :
// `appliquerTheme(null)` posait `data-theme="systeme"`, or le store initialise `theme` à `null` —
// une tablette neuve suivait donc l'OS, l'alternative qu'ADR-0074 déclare rejeter. Le CA disait
// l'inverse de ce que le code faisait. Ces tests dérivent des **puces de CA**, pas du code.

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

  it('la charte ne fait suivre l’OS que sur choix explicite', () => {
    // L'autre moitié de la garantie, et elle vit dans le CSS : tant qu'aucune règle
    // `prefers-color-scheme` ne cible `:root` **nu**, le défaut ne peut pas se remettre à suivre
    // l'appareil. C'est la seule façon dont le défaut corrigé pourrait revenir.
    //
    // *(Une première version comparait ici `appliquerTheme(null)` à lui-même : une assertion qui ne
    // pouvait pas échouer, dans le fichier écrit pour prouver qu'un CA est tenu. Relevée à la revue.)*
    const charte = readFileSync(join(process.cwd(), 'src', 'index.css'), 'utf8')
    const reglesSuivantLOS = [
      ...charte.matchAll(/@media \(prefers-color-scheme:[^)]*\)\s*\{([^}]*)\{/g),
    ]
    expect(reglesSuivantLOS.length).toBeGreaterThan(0)
    for (const [, cible] of reglesSuivantLOS) {
      expect((cible ?? '').trim()).toMatch(/data-theme='systeme'/)
    }
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
