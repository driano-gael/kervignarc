/// <reference types="node" />

// Garde-fou de la règle 13 côté **front** — huit lignes au plus par bloc (ADR-0099, E00US027).
//
// Pendant de `backend/tests/test_commentaires_bornes.py`, **sans cliquet** : `frontend/src` est
// intégralement sous le plafond depuis E00US027, la règle y est donc dure d'emblée. ⚠️ Le compte
// porte sur les **blocs contigus** — deux commentaires que rien ne sépare n'en font qu'un, c'est ce
// qu'un lecteur avale d'un trait. Un bloc plus long n'est plus un avertissement : son raisonnement
// va en ADR / story / registre, et le code garde un renvoi d'une ligne.

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// Depuis la racine du projet Vite et non d'`import.meta.url` : le transform réécrit cette URL en
// schéma non-`file`, que `fileURLToPath` refuse.
const RACINE = join(process.cwd(), 'src')
const PLAFOND = 8
const EXTENSIONS = ['.ts', '.tsx', '.css']

/** Vrai/faux par ligne : cette ligne est-elle **entièrement** du commentaire ?
 *
 * Un commentaire en fin de ligne de code ne compte pas — il n'ouvre pas un bloc à lire d'un trait.
 */
function lignesDeCommentaire(texte: string): boolean[] {
  const marques: boolean[] = []
  let dansBloc = false
  for (const ligne of texte.split('\n')) {
    const nette = ligne.trim()
    if (dansBloc) {
      marques.push(true)
      if (nette.includes('*/')) dansBloc = false
      continue
    }
    if (nette.startsWith('/*')) {
      marques.push(true)
      if (!nette.slice(2).includes('*/')) dansBloc = true
      continue
    }
    marques.push(nette.startsWith('//'))
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
    const regressions = fichiersDuFront().flatMap((chemin) => {
      const trop = blocsTropLongs(readFileSync(chemin, 'utf-8'))
      if (trop.length === 0) return []
      const relatif = chemin.slice(RACINE.length).replace(/\\/g, '/')
      const ou = trop.map(([ligne, taille]) => `l.${ligne} (${taille})`).join(', ')
      return [`${relatif} : ${trop.length} bloc(s) > ${PLAFOND} lignes — ${ou}`]
    })

    expect(regressions, regressions.join('\n')).toEqual([])
  })

  it('sait reconnaître un bloc trop long', () => {
    const trop = blocsTropLongs(`${'// x\n'.repeat(9)}const a = 1\n`)
    expect(trop).toEqual([[1, 9]])
    expect(blocsTropLongs(`${'// x\n'.repeat(8)}const a = 1\n`)).toEqual([])
    expect(blocsTropLongs(`const a = 1 // ${'x '.repeat(9)}\n`)).toEqual([])
  })
})
