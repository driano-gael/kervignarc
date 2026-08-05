// Tests du « départ courant » (retour maquettes du 04/08/2026, A02).
// Les cas dérivent de la question posée — *« savoir sur quel tournoi on est et quel départ »* — et
// des états que le serveur rend déjà, pas de la lecture de l'implémentation (règle 9).

import { describe, expect, it } from 'vitest'
import type { Depart, EtatDepart } from './api'
import { departCourant, libelleEtatDepart } from './courant'

function depart(numero: number, etat: EtatDepart): Depart {
  return {
    id: numero,
    tournoi_id: 1,
    numero,
    horaire: `0${numero}:00`,
    tarif_centimes: 0,
    quota: null,
    etat,
  }
}

describe('departCourant', () => {
  it('un tournoi sans créneau n’a pas de départ courant', () => {
    expect(departCourant([])).toBeNull()
  })

  it('le départ lancé est celui qui compte', () => {
    const liste = [depart(1, 'clos'), depart(2, 'lance'), depart(3, 'ouvert')]
    expect(departCourant(liste)?.numero).toBe(2)
  })

  it('deux créneaux menés de front : le plus avancé, donc le plus petit numéro', () => {
    const liste = [depart(3, 'lance'), depart(2, 'lance')]
    expect(departCourant(liste)?.numero).toBe(2)
  })

  it('avant le premier feu vert, c’est le prochain à ouvrir', () => {
    const liste = [depart(1, 'ouvert'), depart(2, 'ouvert')]
    expect(departCourant(liste)?.numero).toBe(1)
  })

  it('le départ clos ne masque pas celui qui suit', () => {
    const liste = [depart(1, 'clos'), depart(2, 'ouvert')]
    expect(departCourant(liste)?.numero).toBe(2)
  })

  it('une journée entièrement close n’a plus de départ courant', () => {
    // Écrire « départ 3 » d'une journée finie serait faux : l'appelant dira « terminé ».
    expect(departCourant([depart(1, 'clos'), depart(2, 'clos')])).toBeNull()
  })

  it('l’ordre d’arrivée de la liste n’influe pas sur le résultat', () => {
    const liste = [depart(3, 'ouvert'), depart(1, 'clos'), depart(2, 'ouvert')]
    expect(departCourant(liste)?.numero).toBe(2)
  })
})

describe('libelleEtatDepart', () => {
  it.each([
    ['lance', 'en cours'],
    ['ouvert', 'à lancer'],
    ['clos', 'clos'],
  ] as const)('%s se lit « %s »', (etat, attendu) => {
    expect(libelleEtatDepart(depart(1, etat))).toBe(attendu)
  })
})
