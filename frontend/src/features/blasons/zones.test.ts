import { describe, expect, it } from 'vitest'
import {
  ZONES_CANONIQUES,
  ZONES_DEFAUT,
  aUneZoneMarquante,
  basculerZone,
  estVerrouillee,
  type Zone,
} from './zones'

// Le jeu complet, **codé en dur** plutôt qu'importé de `ZONES_CANONIQUES` : un test dont l'entrée
// dérive de la constante que la fonction sous test utilise ne peut plus détecter un changement de
// cette constante. C'est l'oracle du test, il doit rester indépendant du module.
const ZONES_COMPLETES: Zone[] = ['10', '9', '8', '7', '6', '5', '4', '3', '2', '1', 'M']

describe('basculerZone', () => {
  it('replace une zone cochée dans l’ordre canonique, quel que soit l’ordre d’arrivée', () => {
    // L'admin coche 6 en dernier : il doit ressortir à sa place, pas à la fin.
    const actuelles: Zone[] = ['M', '9', '10']
    expect(basculerZone(actuelles, '6')).toEqual(['10', '9', '6', 'M'])
  })

  it('décoche sans dénormaliser l’ordre', () => {
    const actuelles: Zone[] = ['10', '9', '8', '7', '6', 'M']
    expect(basculerZone(actuelles, '8')).toEqual(['10', '9', '7', '6', 'M'])
  })

  it('renormalise AUSSI en décochant, depuis un état désordonné', () => {
    // Le cas qui mord : partir d'un état déjà canonique ne prouve rien de la branche décoche.
    expect(basculerZone(['M', '9', '10'], '9')).toEqual(['10', 'M'])
  })

  it('ne duplique pas une zone déjà cochée (bascule aller-retour)', () => {
    const actuelles: Zone[] = ['10', '9', 'M']
    expect(basculerZone(basculerZone(actuelles, '8'), '8')).toEqual(actuelles)
  })

  it('ne mute pas le tableau reçu', () => {
    const actuelles: Zone[] = ['10', 'M']
    basculerZone(actuelles, '9')
    expect(actuelles).toEqual(['10', 'M'])
  })

  it('reconstitue le triple 40 en retirant 5 → 1 du jeu complet', () => {
    let zones: Zone[] = [...ZONES_COMPLETES]
    for (const zone of ['5', '4', '3', '2', '1'] as Zone[]) {
      zones = basculerZone(zones, zone)
    }
    expect(zones).toEqual(['10', '9', '8', '7', '6', 'M'])
  })
})

describe('estVerrouillee', () => {
  it('verrouille le manqué une fois coché : l’admin ne peut pas le retirer', () => {
    expect(estVerrouillee(['10', '9', 'M'], 'M')).toBe(true)
  })

  it('ne verrouille pas un blason arrivé sans manqué — sinon il serait inéditable', () => {
    // Le cas qui motive le correctif : case ni cochée ni cochable, PUT refusé en 422, et aucune
    // action dans l'UI pour s'en sortir.
    expect(estVerrouillee(['10', '9'], 'M')).toBe(false)
  })

  it('laisse le rattrapage produire un jeu que le domaine accepte', () => {
    expect(basculerZone(['10', '9'], 'M')).toEqual(['10', '9', 'M'])
  })

  it('ne verrouille jamais une zone marquante', () => {
    expect(estVerrouillee(['10', '9', 'M'], '10')).toBe(false)
  })
})

describe('aUneZoneMarquante', () => {
  it('est faux quand il ne reste que le manqué', () => {
    expect(aUneZoneMarquante(['M'])).toBe(false)
  })

  it('est faux sur un jeu vide', () => {
    expect(aUneZoneMarquante([])).toBe(false)
  })

  it('est vrai dès qu’une valeur chiffrée subsiste', () => {
    expect(aUneZoneMarquante(['6', 'M'])).toBe(true)
  })
})

describe('ZONES_DEFAUT', () => {
  it('vaut le jeu complet d’un blason simple', () => {
    expect([...ZONES_DEFAUT]).toEqual(ZONES_COMPLETES)
  })

  it('n’est pas un alias du vocabulaire', () => {
    // Fil-piège, miroir de celui du domaine. Si vous ajoutez une zone à ZONES_CANONIQUES (X, pour
    // le départage FFTA d'EPIC-06), c'est CETTE ligne qui doit sauter — pas ZONES_DEFAUT : une
    // zone ajoutée au vocabulaire ne doit pas se pré-cocher en silence sur tout nouveau blason.
    expect([...ZONES_DEFAUT]).toEqual([...ZONES_CANONIQUES])
    expect(ZONES_DEFAUT).not.toBe(ZONES_CANONIQUES)
  })
})
