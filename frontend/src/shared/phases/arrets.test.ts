// Le modèle des arrêts programmés (E05US033, ADR-0091) — tests du **front**, écrits depuis le CA.
//
// Ce fichier ne teste ni le déclenchement ni le gel : ils sont serveur, et leurs oracles sont
// `backend/tests/test_domain_arret_programme.py` et `test_service_arrets_programmes.py`. Ici on ne
// garde que la **conversion** « ce que l'écran affiche ↔ ce qui part au serveur », qui est la seule
// règle que le front porte réellement.
//
// ⚠️ **Deux gardes valent d'être lues** :
//
// - `null vs undefined` : c'est la distinction qui décide si un `PUT` **efface** le réglage ou s'il ne
//   part pas du tout. Les confondre effacerait le planning d'un organisateur en train de retaper un
//   champ — un défaut silencieux, puisque la requête réussirait.
// - la **clé de ligne** : sans elle, supprimer un arrêt ferait glisser les valeurs saisies d'une ligne
//   à l'autre. Le test la vérifie par sa seule propriété observable — deux lignes neuves diffèrent.

import { describe, expect, it } from 'vitest'

import {
  ARRETS_PAR_DEFAUT,
  type EtatArrets,
  TOURS_MAX_REGLABLES,
  decrire,
  depuisEtape,
  estValide,
  ligneNeuve,
  toursEnDoublon,
  versArrets,
  versDecoupage,
} from './arrets'

function etat(tours: string, ...arrets: [string, 'phase' | 'depart'][]): EtatArrets {
  return {
    tours,
    lignes: arrets.map(([apresTour, portee], i) => ({ cle: `c${i}`, apresTour, portee })),
  }
}

describe('le défaut, qui est l’enchaînement automatique', () => {
  it('ne porte aucun arrêt et aucun découpage', () => {
    // CA — « une phase sans arrêt programmé se comporte exactement comme aujourd'hui ». Côté front,
    // cela veut dire qu'un écran ouvert puis soumis sans y toucher n'envoie **rien** de neuf.
    expect(ARRETS_PAR_DEFAUT.lignes).toEqual([])
    expect(versDecoupage(ARRETS_PAR_DEFAUT)).toBeNull()
    expect(versArrets(ARRETS_PAR_DEFAUT)).toEqual([])
    expect(estValide(ARRETS_PAR_DEFAUT)).toBe(true)
  })

  it('se reconstruit à l’identique depuis une étape qui n’a rien', () => {
    expect(depuisEtape(null, null)).toEqual({ tours: '', lignes: [] })
    expect(depuisEtape(undefined, undefined)).toEqual({ tours: '', lignes: [] })
  })
})

describe('la conversion vers le serveur', () => {
  it('transporte une liste d’arrêts dans l’ordre de saisie', () => {
    // CA — « plusieurs par phase : c'est une liste, pas un arrêt unique ».
    expect(versArrets(etat('', ['2', 'phase'], ['5', 'depart']))).toEqual([
      { apres_tour: 2, portee: 'phase' },
      { apres_tour: 5, portee: 'depart' },
    ])
  })

  it('distingue « efface le découpage » de « ne soumets pas »', () => {
    // ⚠️ La garde qui compte. `null` = efface (l'édition est totale côté API), `undefined` = illisible.
    expect(versDecoupage(etat(''))).toBeNull()
    expect(versDecoupage(etat('2'))).toEqual({ nb_tours: 2 })
    expect(versDecoupage(etat('deux'))).toBeUndefined()
    expect(versDecoupage(etat('0'))).toBeUndefined()
    expect(versDecoupage(etat('2.5'))).toBeUndefined()
    expect(versDecoupage(etat(String(TOURS_MAX_REGLABLES + 1)))).toBeUndefined()
  })

  it('refuse de soumettre dès qu’une seule ligne est illisible', () => {
    // Tout ou rien : envoyer les lignes lisibles et taire les autres perdrait du planning en silence.
    expect(versArrets(etat('', ['2', 'phase'], ['', 'phase']))).toBeUndefined()
    expect(versArrets(etat('', ['2', 'phase'], ['zéro', 'phase']))).toBeUndefined()
    expect(estValide(etat('', ['2', 'phase'], ['', 'phase']))).toBe(false)
  })

  it('fait l’aller-retour depuis une étape déjà réglée', () => {
    const reconstruit = depuisEtape(
      [
        { apres_tour: 2, portee: 'phase' },
        { apres_tour: 5, portee: 'depart' },
      ],
      { nb_tours: 4 },
    )

    expect(reconstruit.tours).toBe('4')
    expect(versArrets(reconstruit)).toEqual([
      { apres_tour: 2, portee: 'phase' },
      { apres_tour: 5, portee: 'depart' },
    ])
    expect(versDecoupage(reconstruit)).toEqual({ nb_tours: 4 })
  })
})

describe('les doublons, dits à l’écran plutôt que refusés en bloc', () => {
  it('nomme le tour posé deux fois', () => {
    // Le serveur refuse déjà (`ArretProgrammeInvalide`, 422) et fait autorité. Le dire ici sert
    // seulement à montrer **quelle** ligne corriger, au lieu d'un refus global à la soumission.
    expect(toursEnDoublon(etat('', ['3', 'phase'], ['3', 'depart']))).toEqual([3])
    expect(estValide(etat('', ['3', 'phase'], ['3', 'depart']))).toBe(false)
  })

  it('ne voit aucun doublon sur des tours distincts', () => {
    expect(toursEnDoublon(etat('', ['2', 'phase'], ['3', 'phase']))).toEqual([])
  })

  it('ignore les lignes illisibles au lieu de les compter ensemble', () => {
    // Deux champs vides ne sont pas « deux arrêts après le même tour » : ce sont deux lignes en cours
    // de saisie. Les signaler en doublon ferait clignoter une alerte fausse dès le second ajout.
    expect(toursEnDoublon(etat('', ['', 'phase'], ['', 'phase']))).toEqual([])
  })
})

describe('la clé de ligne', () => {
  it('diffère d’une ligne neuve à l’autre', () => {
    // ⚠️ Sa seule propriété observable, et elle suffit : c'est l'unicité qui empêche React de
    // réutiliser une ligne par index — donc de faire glisser la valeur saisie de la ligne suivante
    // dans le champ d'une ligne supprimée.
    const cles = new Set([ligneNeuve().cle, ligneNeuve().cle, ligneNeuve().cle])
    expect(cles.size).toBe(3)
  })

  it('donne une ligne neuve de portée « cette phase seule »', () => {
    // Le défaut le moins intrusif : couper une phase n'éteint pas la salle.
    expect(ligneNeuve().portee).toBe('phase')
  })
})

describe('la phrase de relecture', () => {
  it('dit ce qu’un arrêt de phase coupe, et ce qu’il laisse', () => {
    expect(decrire({ cle: 'c', apresTour: '3', portee: 'phase' })).toContain('cette phase')
    expect(decrire({ cle: 'c', apresTour: '3', portee: 'phase' })).toContain(
      'Les autres continuent',
    )
  })

  it('dit qu’un arrêt de créneau laisse chaque phase finir son tour', () => {
    // CA — l'arbitrage du commanditaire du 18/08/2026. C'est la nuance que l'organisateur doit lire
    // avant de valider son planning : l'arrêt n'est **pas** simultané.
    const phrase = decrire({ cle: 'c', apresTour: '3', portee: 'depart' })
    expect(phrase).toContain('tout le créneau')
    expect(phrase).toContain('finissant d’abord le tour')
  })

  it('invite à compléter plutôt que d’afficher un tour inventé', () => {
    expect(decrire({ cle: 'c', apresTour: '', portee: 'phase' })).toContain('Indiquez')
  })
})
