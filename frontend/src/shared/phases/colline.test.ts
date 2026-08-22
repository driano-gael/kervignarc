// E05US027 — le modèle du réglage de colline : conversion, validation, borne.
//
// Ce que ces tests gardent réellement, c'est le **miroir** de `domain/colline.py::portee_maximale`.
// Le serveur fait autorité et borne à la lecture ; ce miroir n'existe que pour l'atelier de
// **formats**, où aucune phase n'est posée et où il n'y a donc aucune lecture à appeler. Sa dérive
// ne produirait qu'un avertissement faux — jamais un tournoi faux —, mais un avertissement faux
// apprend à ignorer les avertissements.

import { describe, expect, it } from 'vitest'

import {
  COLLINE_PAR_DEFAUT,
  decrireBorne,
  decrireBorneConnue,
  depuisReglage,
  estValide,
  nommerFormat,
  porteeMaximale,
  versReglage,
} from './colline'

describe('la conversion écran ↔ serveur', () => {
  it('part sur un King of the Hill de 5 manches', () => {
    // Le défaut du domaine (`ConfigurationColline`), repris à l'identique : deux défauts qui
    // divergent feraient qu'une phase créée sans y toucher n'a pas le réglage annoncé à l'écran.
    expect(COLLINE_PAR_DEFAUT).toEqual({ manches: '5', portee: '1' })
    expect(versReglage(COLLINE_PAR_DEFAUT)).toEqual({ nb_manches: 5, portee_de_defi: 1 })
  })

  it('reconstruit l’état d’édition depuis un réglage existant', () => {
    expect(depuisReglage({ nb_manches: 6, portee_de_defi: 2 })).toEqual({
      manches: '6',
      portee: '2',
    })
  })

  it('retombe sur le défaut quand rien n’est réglé', () => {
    // `null` = non réglée, ce qui est licite : le type se choisit avant ses paramètres.
    expect(depuisReglage(null)).toEqual(COLLINE_PAR_DEFAUT)
  })

  it('refuse un champ vide sans le confondre avec un effacement', () => {
    // ⚠️ `undefined` veut dire « illisible », **pas** « efface ». L'appelant ne le transmet jamais
    // tel quel — il bloque sa soumission. Le champ reste une chaîne précisément pour qu'il puisse
    // être vidé pendant qu'on le retape.
    expect(versReglage({ manches: '', portee: '1' })).toBeUndefined()
    expect(versReglage({ manches: '5', portee: '' })).toBeUndefined()
    expect(estValide({ manches: '', portee: '1' })).toBe(false)
  })

  it('refuse ce que le serveur refuserait', () => {
    expect(versReglage({ manches: '0', portee: '1' })).toBeUndefined()
    expect(versReglage({ manches: '5', portee: '0' })).toBeUndefined()
    expect(versReglage({ manches: '65', portee: '1' })).toBeUndefined()
    expect(versReglage({ manches: '5', portee: '65' })).toBeUndefined()
    expect(versReglage({ manches: '2,5', portee: '1' })).toBeUndefined()
  })
})

describe('le nom du format', () => {
  it('nomme ce que la portée désigne, dans le vocabulaire du club', () => {
    // Le catalogue n'expose qu'un type « colline » parce que le moteur est le même (règle 2), mais
    // le référentiel §10.1 décrit **deux** formats et c'est ainsi que le club en parle. Un nombre
    // nu sous un champ ne dit rien à l'organisateur.
    expect(nommerFormat(1)).toBe('King of the Hill')
    expect(nommerFormat(2)).toBe('Ladder')
    expect(nommerFormat(5)).toBe('Ladder')
  })
})

describe('la borne de portée', () => {
  it('vaut effectif − 1 — un défi ne porte pas au-delà du dernier rang', () => {
    expect(porteeMaximale(8)).toBe(7)
    expect(porteeMaximale(4)).toBe(3)
  })

  it('vaut zéro sous deux tireurs, et non un', () => {
    // ⚠️ La réponse honnête est **0** : aucun défi n'est appariable. Annoncer « 1 » laisserait
    // croire qu'une colline à un archer se joue. Le service rend le même 0 sur une phase vide.
    expect(porteeMaximale(1)).toBe(0)
    expect(porteeMaximale(0)).toBe(0)
  })

  it('dit la borne en clair sans rien reprocher quand le réglage tient', () => {
    expect(decrireBorne(8, 2)).toBe('8 archers : un défi porte au plus sur 7 rangs.')
  })

  it('nomme l’écart quand le réglage dépasse la borne', () => {
    // C'est l'objet du CA : sans cette phrase, l'organisateur ne l'apprend ni à l'enregistrement
    // (le serveur borne à la lecture, il ne lève pas) ni le jour J — il voit simplement des défis
    // plus courts que prévu.
    expect(decrireBorne(4, 5)).toContain('Vous avez réglé 5')
    expect(decrireBorne(4, 5)).toContain('3 rangs seront appliqués')
  })

  it('accorde le singulier sur une colline de deux archers', () => {
    // Le cas limite que la revue du suisse a fait corriger sur sa jumelle, pour avoir réécrit la
    // phrase à la main dans l'écran de saisie : « 1 archers » y était sorti.
    expect(decrireBorne(2, 1)).toBe('2 archers : un défi porte au plus sur 1 rang.')
  })

  it('dit « aucun défi appariable » plutôt qu’une borne de zéro rang', () => {
    expect(decrireBorne(1, 1)).toBe(
      '1 archer : aucun défi n’est appariable (il en faut au moins deux).',
    )
    // ⚠️ **Singulier après zéro**, comme sa jumelle du suisse : c'est la règle du français, et
    // l'écrire au pluriel ici aurait fait diverger deux phrases voisines du même atelier.
    expect(decrireBorne(0, 1)).toContain('0 archer :')
  })

  it('rend la même phrase sur une borne fournie par le serveur', () => {
    // ⚠️ Cette variante existe pour que l'écran de saisie **n'ait pas à recalculer** : il reçoit
    // `portee_maximale` dans sa réponse d'état, et deux arithmétiques pour une même règle divergent
    // tôt ou tard. Le test vérifie que les deux chemins écrivent bien la même chose.
    expect(decrireBorneConnue(8, 2, porteeMaximale(8))).toBe(decrireBorne(8, 2))
    expect(decrireBorneConnue(4, 5, porteeMaximale(4))).toBe(decrireBorne(4, 5))
  })

  it('suit la borne du serveur même quand elle diverge du miroir', () => {
    // Le point de la variante : c'est le **serveur** qui fait autorité. Si les deux venaient à ne
    // pas dire la même chose, l'écran de saisie doit annoncer celle du serveur — pas la sienne.
    expect(decrireBorneConnue(8, 2, 3)).toContain('3 rangs')
  })
})
