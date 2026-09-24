import { describe, expect, it } from 'vitest'
import type { Grain, SaisirVolee, Serie, Volee } from './api'
import {
  heureSaisie,
  libelleGrain,
  nouvelIdentifiant,
  pointsZone,
  prochaineASaisir,
  quelSaisiePar,
  serieOptimiste,
  cumulSaisi,
  totalVolee,
  voleeApresEnregistrement,
  voleeExistante,
} from './volees'

function volee(numero: number, valeurs: string[], verrouillee = false): Volee {
  return {
    numero,
    valeurs,
    saisie_par: null,
    validee_par: verrouillee ? 'ROUX' : null,
    en_correction: false,
    correction_ouverte_par: null,
    lot_validation: verrouillee ? 1 : null,
    verrouillee,
    saisie_le: null,
  }
}

describe('pointsZone — le miroir du domaine', () => {
  // ⚠️ **Moitié front d'un cliquet en deux moitiés** ; l'autre fige la même liste côté domaine
  // (`test_domain_blason.py`) et renvoie ici. Une zone ajoutée casse alors **un** test au lieu de
  // zéro, et qui le répare lit le pointeur vers l'autre langage. Ça ne **relie** pas les deux
  // langages pour autant : seul `points_par_zone` le fera (`DETTE-111`).
  // Les onze valeurs sont celles de `ZoneScore` (art. B.2.1.2) — pas de « X », centre du 10.
  it('donne à chaque zone du vocabulaire FFTA sa valeur, M valant 0', () => {
    const zones = ['10', '9', '8', '7', '6', '5', '4', '3', '2', '1', 'M']
    expect(zones.map(pointsZone)).toEqual([10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0])
  })
})

describe('cumulSaisi', () => {
  it('somme toutes les volées saisies, validées ou non', () => {
    // Le cas qui motive la fonction : avec le grain « à la fin de la série », **aucune** volée n'est
    // validée avant le passage du scoreur. `Serie.cumul` vaut alors 0 tout au long de la série, et
    // le rappel demandé en S02 (« en permanence, c'est un bon rappel sur la cible ») affichait zéro.
    expect(cumulSaisi([volee(1, ['10', '9', '8']), volee(2, ['9', '9', '9'])])).toBe(54)
  })

  it('compte de la même façon une volée verrouillée par le scoreur', () => {
    expect(cumulSaisi([volee(1, ['10', '9', '8'], true), volee(2, ['9', '9', '9'])])).toBe(54)
  })

  it('vaut 0 sans volée, et compte le M pour 0', () => {
    expect(cumulSaisi([])).toBe(0)
    expect(cumulSaisi([volee(1, ['M', 'M', '10'])])).toBe(10)
  })
})

describe('pointsZone', () => {
  it('« M » (manqué) vaut 0 point', () => {
    expect(pointsZone('M')).toBe(0)
  })

  it('une zone numérique vaut sa valeur', () => {
    expect(pointsZone('10')).toBe(10)
    expect(pointsZone('7')).toBe(7)
  })

  it('une valeur inattendue vaut 0 (défensif)', () => {
    expect(pointsZone('X')).toBe(0)
  })
})

describe('totalVolee', () => {
  it('somme les points des flèches', () => {
    expect(totalVolee(['10', '9', 'M'])).toBe(19)
  })

  it('une volée vide vaut 0', () => {
    expect(totalVolee([])).toBe(0)
  })
})

describe('prochaineASaisir', () => {
  it('sans aucune volée, la première est à saisir', () => {
    expect(prochaineASaisir([], 20)).toBe(1)
  })

  it('avance dès qu’une volée est saisie, même non validée (le verrou est l’acte du scoreur)', () => {
    // 1 saisie mais pas verrouillée : le marqueur passe quand même à la 2.
    expect(prochaineASaisir([volee(1, ['9', '9', '9'])], 20)).toBe(2)
  })

  it('reprend le premier trou (une volée sautée reste à saisir)', () => {
    const volees = [volee(1, ['10', '9', '8']), volee(3, ['8', '8', '8'])]
    expect(prochaineASaisir(volees, 20)).toBe(2)
  })

  it('toutes les volées saisies → on reste sur la dernière (édition via le navigateur)', () => {
    const volees = [volee(1, ['10', '9', '8']), volee(2, ['9', '9', '9'])]
    expect(prochaineASaisir(volees, 2)).toBe(2)
  })

  it('une volée rendue DÉJÀ ressaisie ne retient plus le pavé', () => {
    // ⚠️ `en_correction` ne tombe qu'à la **revalidation du scoreur** : sans le paramètre `apres`,
    // le pavé rouvrait en boucle la volée qu'on venait d'enregistrer, et un lot de deux volées
    // devenait infranchissable au doigt (relevé en revue).
    const volees = [
      {
        numero: 1,
        valeurs: ['6', '6', '6'],
        saisie_par: 'DURAND',
        validee_par: 'ROUX',
        verrouillee: false,
        en_correction: true,
        correction_ouverte_par: 'MARTIN',
        lot_validation: 1,
        saisie_le: null,
      },
      {
        numero: 2,
        valeurs: ['10', '9', '8'],
        saisie_par: 'DURAND',
        validee_par: 'ROUX',
        verrouillee: false,
        en_correction: true,
        correction_ouverte_par: 'MARTIN',
        lot_validation: 1,
        saisie_le: null,
      },
    ]

    expect(prochaineASaisir(volees, 2, 1)).toBe(2)
  })

  it('une volée rendue passe devant dans le pavé (le marqueur la trouve sans chercher)', () => {
    const volees = [
      {
        numero: 1,
        valeurs: ['10', '9', '8'],
        saisie_par: 'DURAND',
        validee_par: 'ROUX',
        verrouillee: false,
        en_correction: true,
        correction_ouverte_par: 'MARTIN',
        lot_validation: 1,
        saisie_le: null,
      },
      {
        numero: 2,
        valeurs: ['9', '9', '9'],
        saisie_par: 'DURAND',
        validee_par: 'ROUX',
        verrouillee: true,
        en_correction: false,
        correction_ouverte_par: null,
        lot_validation: 2,
        saisie_le: null,
      },
    ]

    // Toutes les volées sont saisies : sans la clause d'E16US019, on retombait sur la dernière
    // du barème — verrouillée, avec le message « sa correction relève du scoreur ».
    expect(prochaineASaisir(volees, 2)).toBe(1)
  })
})

describe('nouvelIdentifiant', () => {
  it('produit un UUID quand crypto.randomUUID est disponible (contexte sécurisé)', () => {
    expect(nouvelIdentifiant()).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    )
  })
})

describe('voleeExistante', () => {
  it('retrouve une volée déjà saisie pour la rééditer', () => {
    const v = volee(3, ['8', '8', '8'])
    expect(voleeExistante([v], 3)).toEqual(v)
  })

  it('rend null si la volée n’a pas encore été saisie', () => {
    expect(voleeExistante([], 3)).toBeNull()
  })
})

describe('libelleGrain', () => {
  it('fin de série', () => {
    expect(libelleGrain({ grain: 'fin_de_serie', n_volees: null })).toBe(
      'Validation à la fin de la série',
    )
  })

  it('fin de duel', () => {
    expect(libelleGrain({ grain: 'fin_de_duel', n_volees: null })).toBe(
      'Validation à la fin du duel',
    )
  })

  it('toutes les N volées reprend le N', () => {
    const grain: Grain = { grain: 'toutes_les_n_volees', n_volees: 2 }
    expect(libelleGrain(grain)).toBe('Validation toutes les 2 volées')
  })

  it('grain absent → mention explicite', () => {
    expect(libelleGrain(null)).toBe('Grain de validation non défini')
  })
})

describe('heureSaisie', () => {
  it('formate l’heure locale en HHhMM', () => {
    // Entrée ISO **sans** offset → JS l'interprète en heure locale, donc `getHours()` est
    // déterministe quelle que soit la TZ du runner. En production, `saisie_le` est UTC (offset `Z`)
    // et s'affiche à l'heure murale de la salle ; ce test valide le **format**, pas la conversion TZ.
    expect(heureSaisie('2026-07-19T09:05:00')).toBe('09h05')
  })

  it('horodatage absent → chaîne vide', () => {
    expect(heureSaisie(null)).toBe('')
  })

  it('horodatage illisible → chaîne vide', () => {
    expect(heureSaisie('pas une date')).toBe('')
  })
})

describe('quelSaisiePar', () => {
  it('nouvelle volée → le marqueur actif signe', () => {
    expect(quelSaisiePar(null, 'DURAND')).toBe('DURAND')
  })

  it('ré-édition d’une volée existante → null (le domaine préserve le marqueur d’origine)', () => {
    const existante: Volee = {
      numero: 1,
      valeurs: ['10', '9', '8'],
      saisie_par: 'DURAND',
      validee_par: null,
      verrouillee: false,
      en_correction: false,
      correction_ouverte_par: null,
      lot_validation: null,
      saisie_le: null,
    }
    expect(quelSaisiePar(existante, 'MARTIN')).toBeNull()
  })
})

describe('serieOptimiste', () => {
  const corps = (numero: number, valeurs: string[]): SaisirVolee => ({
    tournoi_id: 1,
    archer_id: 7,
    numero,
    valeurs,
    saisie_par: 'DURAND',
    identifiant_saisie: `id-${numero}`,
  })

  it('injecte la volée en attente dans une série vide (le marqueur peut avancer)', () => {
    const serie = serieOptimiste(undefined, corps(1, ['10', '9', '9']))
    expect(serie.tournoi_id).toBe(1)
    expect(serie.archer_id).toBe(7)
    expect(serie.cumul).toBe(0)
    expect(serie.volees).toMatchObject([
      {
        numero: 1,
        valeurs: ['10', '9', '9'],
        saisie_par: 'DURAND',
        verrouillee: false,
        en_attente: true,
      },
    ])
  })

  it('la prochaine volée avance sur une série optimiste (comme sur une vraie saisie)', () => {
    const serie = serieOptimiste(undefined, corps(1, ['9', '9', '9']))
    expect(prochaineASaisir(serie.volees, 20)).toBe(2)
  })

  it('ajoute la volée sans toucher aux précédentes ni au cumul officiel', () => {
    const base: Serie = {
      tournoi_id: 1,
      archer_id: 7,
      cumul: 55,
      volees: [
        {
          numero: 1,
          valeurs: ['10', '9', '8'],
          saisie_par: 'DURAND',
          validee_par: 'ROUX',
          verrouillee: true,
          en_correction: false,
          correction_ouverte_par: null,
          lot_validation: 1,
          saisie_le: '2026-07-19T09:00:00Z',
        },
      ],
    }
    const serie = serieOptimiste(base, corps(2, ['9', '9', '9']))
    expect(serie.cumul).toBe(55) // inchangé : le cumul ne compte que les volées validées
    expect(serie.volees.map((v) => v.numero)).toEqual([1, 2])
    // la volée validée n'est pas altérée
    expect(serie.volees.find((v) => v.numero === 1)?.verrouillee).toBe(true)
  })

  it('remplace la volée du même numéro (ré-édition hors-ligne), sans doublon', () => {
    const premiere = serieOptimiste(undefined, corps(1, ['5', '5', '5']))
    const corrigee = serieOptimiste(premiere, corps(1, ['10', '10', '10']))
    expect(corrigee.volees).toMatchObject([{ numero: 1, valeurs: ['10', '10', '10'] }])
  })

  it('préserve la validation et le lot d’une volée rendue par le scoreur', () => {
    // ADR-0109, décision 3 versant hors-ligne : sans cette clause, la ressaisie d'une volée
    // rendue la repasserait « jamais validée » — elle disparaîtrait des volées comptées à
    // l'écran le temps de la reconnexion, c'est-à-dire exactement ce que l'US achète.
    const base: Serie = {
      tournoi_id: 1,
      archer_id: 7,
      cumul: 27,
      volees: [
        {
          numero: 1,
          valeurs: ['10', '9', '8'],
          saisie_par: 'DURAND',
          validee_par: 'ROUX',
          verrouillee: false,
          en_correction: true,
          correction_ouverte_par: 'MARTIN',
          lot_validation: 3,
          saisie_le: '2026-09-11T09:00:00Z',
        },
      ],
    }

    const serie = serieOptimiste(base, corps(1, ['6', '6', '6']))

    expect(serie.volees).toMatchObject([
      {
        numero: 1,
        valeurs: ['6', '6', '6'],
        validee_par: 'ROUX',
        en_correction: true,
        correction_ouverte_par: 'MARTIN',
        lot_validation: 3,
        en_attente: true,
      },
    ])
  })

  it('ne recopie PAS la validation quand la volée remplacée n’était pas rendue', () => {
    // Oracle de non-garde : sans ce cas, « on recopie toujours l'existant » passerait le test
    // précédent tout en ressuscitant une validation que le scoreur n'a jamais donnée.
    const base: Serie = {
      tournoi_id: 1,
      archer_id: 7,
      cumul: 0,
      volees: [
        {
          numero: 1,
          valeurs: ['10', '9', '8'],
          saisie_par: 'DURAND',
          validee_par: null,
          verrouillee: false,
          en_correction: false,
          correction_ouverte_par: null,
          lot_validation: null,
          saisie_le: null,
        },
      ],
    }

    const serie = serieOptimiste(base, corps(1, ['6', '6', '6']))

    expect(serie.volees[0]).toMatchObject({
      validee_par: null,
      en_correction: false,
      lot_validation: null,
    })
  })

  it('retombe sur getRandomValues quand randomUUID est absent (LAN http, hors contexte sécurisé)', () => {
    const original = globalThis.crypto.randomUUID
    // Simule un contexte non sécurisé : `randomUUID` y est absent de l'objet `crypto`.
    // @ts-expect-error — on retire volontairement la méthode pour exercer le repli.
    globalThis.crypto.randomUUID = undefined
    try {
      const id = nouvelIdentifiant()
      // UUID v4 : 13ᵉ nibble = 4, 17ᵉ ∈ {8,9,a,b}.
      expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i)
      expect(id).not.toBe(nouvelIdentifiant())
    } finally {
      globalThis.crypto.randomUUID = original
    }
  })
})

describe('voleeApresEnregistrement', () => {
  const rendue = (numero: number) => ({
    numero,
    valeurs: ['10', '9', '8'],
    saisie_par: 'DURAND',
    validee_par: 'ROUX',
    verrouillee: false,
    en_correction: true,
    correction_ouverte_par: 'MARTIN',
    lot_validation: 1,
    saisie_le: null,
  })
  const verrouillee = (numero: number) => ({
    ...rendue(numero),
    verrouillee: true,
    en_correction: false,
  })

  it('rend la main au mode automatique sur une volée ordinaire', () => {
    expect(voleeApresEnregistrement([verrouillee(1)], 1)).toBeNull()
  })

  it('vise la suivante DU LOT quand il en reste une', () => {
    expect(voleeApresEnregistrement([rendue(1), rendue(2)], 1)).toBe(2)
  })

  it('ne saute JAMAIS sur une volée verrouillée quand le lot est épuisé', () => {
    // Le cas par défaut des bases migrées (reprise 0054 : un lot par volée). Rendre la main au
    // mode automatique épinglerait la dernière du barème — verrouillée, pavé inécrivable.
    expect(voleeApresEnregistrement([rendue(1), verrouillee(2), verrouillee(3)], 1)).toBe(1)
  })
})
