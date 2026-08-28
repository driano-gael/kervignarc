/// <reference types="node" />

// Garde-fou de la règle 13 côté **front** — huit lignes au plus par bloc (ADR-0099, E00US027).
//
// Pendant de `backend/tests/test_commentaires_bornes.py`, **sans cliquet** : `frontend/src` a été
// ramené sous le plafond par E00US027, il n'y avait donc aucune baseline à conserver. ⚠️ Le compte
// porte sur les **blocs contigus** — deux commentaires que rien ne sépare n'en font qu'un, c'est ce
// qu'un lecteur avale d'un trait. Un bloc plus long n'est plus un avertissement : son raisonnement
// va en ADR / story / registre, et le code garde un renvoi d'une ligne.

// ⚠️ **Périmètre : `frontend/src` en `.ts` / `.tsx` / `.css`, tests compris** — plus strict que le
// backend, qui exclut `backend/tests/` (`DETTE-088`). C'est la couverture cible, pas un excès : le
// gap est côté backend. Hors porte : `frontend/*.config.*` et `atlas/statique/`.
//
// ⚠️ **Limites connues du détecteur, assumées** (`DETTE-088`) : une ligne vide coupe un bloc, donc
// le plafond borne le paragraphe et non la zone de commentaire ; et un gabarit (template literal)
// contenant des lignes `//` ou une paire `/*` serait compté à tort. Aucun cas aujourd'hui.

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// Depuis la racine du projet Vite et non d'`import.meta.url` : le transform réécrit cette URL en
// schéma non-`file`, que `fileURLToPath` refuse.
const RACINE = join(process.cwd(), 'src')
const PLAFOND = 8
const EXTENSIONS = ['.ts', '.tsx', '.css']

/** Un `/*` ouvert que rien ne referme sur cette ligne — vrai aussi pour `{/*` et pour un `/*` posé
 * après du code, deux formes qu'une comparaison sur le début de ligne manquait (revue E00US027).
 */
function resteOuvert(ligne: string): boolean {
  return ligne.lastIndexOf('/*') > ligne.lastIndexOf('*/')
}

/** Vrai/faux par ligne : cette ligne est-elle **entièrement** du commentaire ?
 *
 * Un commentaire en fin de ligne de code ne compte pas — il n'ouvre pas un bloc à lire d'un trait.
 * ⚠️ Une ligne de code qui **ouvre** un `/*` reste comptée comme code, mais les suivantes sont dans
 * le bloc : c'est volontairement sur-strict, un faux positif d'une ligne valant mieux qu'un trou.
 */
function lignesDeCommentaire(texte: string): boolean[] {
  const marques: boolean[] = []
  let dansBloc = false
  for (const ligne of texte.split('\n')) {
    const nette = ligne.trim()
    if (dansBloc) {
      marques.push(true)
      if (nette.includes('*/')) dansBloc = resteOuvert(nette)
      continue
    }
    // Testé avant `/*` : un `//` qui cite un `/*` en prose n'ouvre pas de bloc.
    if (nette.startsWith('//')) {
      marques.push(true)
      continue
    }
    marques.push(nette.startsWith('/*') || nette.startsWith('{/*'))
    dansBloc = resteOuvert(nette)
  }
  return marques
}

/** Les blocs contigus dépassant `PLAFOND`, en `(première ligne, longueur)`. */
function blocsTropLongs(texte: string): Array<[number, number]> {
  const marques = lignesDeCommentaire(texte)
  const trouves: Array<[number, number]> = []
  let debut: number | null = null
  marques.forEach((marque, i) => {
    if (marque && debut === null) debut = i
    else if (!marque && debut !== null) {
      if (i - debut > PLAFOND) trouves.push([debut + 1, i - debut])
      debut = null
    }
  })
  if (debut !== null && marques.length - debut > PLAFOND) {
    trouves.push([debut + 1, marques.length - debut])
  }
  return trouves
}

function fichiersDuFront(dossier: string = RACINE): string[] {
  const sortie: string[] = []
  for (const entree of readdirSync(dossier)) {
    const chemin = join(dossier, entree)
    if (statSync(chemin).isDirectory()) sortie.push(...fichiersDuFront(chemin))
    else if (EXTENSIONS.some((ext) => entree.endsWith(ext))) sortie.push(chemin)
  }
  return sortie
}

describe('règle 13 — bornes des commentaires du front', () => {
  it('aucun fichier ne porte de bloc de plus de huit lignes', () => {
    const fichiers = fichiersDuFront()
    // ⚠️ Sans cette borne, un scan qui ne lit rien rend la porte **verte et vide** — le mode de
    // panne que cette US reproche par ailleurs aux témoins mockés (relevé en revue).
    expect(fichiers.length, `scan vide ou partiel depuis ${RACINE}`).toBeGreaterThan(300)

    const regressions = fichiers.flatMap((chemin) => {
      const trop = blocsTropLongs(readFileSync(chemin, 'utf-8'))
      if (trop.length === 0) return []
      const relatif = chemin.slice(RACINE.length).replace(/\\/g, '/')
      const ou = trop.map(([ligne, taille]) => `l.${ligne} (${taille})`).join(', ')
      return [`${relatif} : ${trop.length} bloc(s) > ${PLAFOND} lignes — ${ou}`]
    })

    expect(regressions, regressions.join('\n')).toEqual([])
  })

  it('fige la borne : neuf lignes rougissent, huit passent', () => {
    expect(blocsTropLongs(`${'// x\n'.repeat(9)}const a = 1\n`)).toEqual([[1, 9]])
    expect(blocsTropLongs(`${'// x\n'.repeat(8)}const a = 1\n`)).toEqual([])
    expect(blocsTropLongs(`const a = 1 // ${'x '.repeat(9)}\n`)).toEqual([])
  })

  // ⚠️ Ces trois formes étaient **invisibles** au détecteur livré en 1ʳᵉ passe, et la branche `/* */`
  // n'avait aucun cas : 13 blocs survivaient dont deux de 15 lignes (relevé par quatre axes).
  it('voit le JSX, le JSDoc et le CSS', () => {
    expect(blocsTropLongs(`{/* x\n${'   y\n'.repeat(8)}*/}\n<div />\n`)).toEqual([[1, 10]])
    expect(blocsTropLongs(`/**\n${' * y\n'.repeat(8)} */\nconst a = 1\n`)).toEqual([[1, 10]])
    expect(blocsTropLongs(`/* a\n${'   y\n'.repeat(8)}   z */\n.x { color: red }\n`)).toEqual([
      [1, 10],
    ])
    expect(blocsTropLongs(`const a = 1 /* x\n${'   y\n'.repeat(9)}*/\n`)).toEqual([[2, 10]])
    expect(blocsTropLongs(`/* a */ /* b\n${'   y\n'.repeat(9)}*/\n`)).toEqual([[1, 11]])
  })

  it('fige les deux limites assumées : ligne vide et commentaire cité', () => {
    expect(blocsTropLongs(`${'// x\n'.repeat(8)}\n${'// x\n'.repeat(8)}`)).toEqual([])
    expect(blocsTropLongs(`${'// voir /* ceci */\n'.repeat(2)}const a = 1\n`)).toEqual([])
  })
})
