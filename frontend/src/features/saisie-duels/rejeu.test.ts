// Tests de `rejouerActes` (E04US013, ADR-0037) — rejeu de la file hors-ligne des duels. On stube
// l'envoi : succès, panne réseau (le `fetch` rejette), refus serveur (`ErreurApi`). Le zéro-doublon
// est garanti côté serveur (idempotence, ADR-0036) ; ici on vérifie l'**ordre** (manches → barrage →
// validation), l'**arrêt** sur panne/transitoire, et le **retrait** des refus définitifs. Jumeau du
// test de rejeu de la qualif.

import { describe, expect, it, vi } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import type { ActeDuelEnFile } from '../../shared/stores/fileDuelsHorsLigneStore'
import { rejouerActes } from './rejeu'

function manche(numero: number): ActeDuelEnFile {
  return {
    type: 'manche',
    tournoi_id: 1,
    phase_id: 2,
    match_numero: 1,
    numero,
    valeurs_haut: ['10', '10', '10'],
    valeurs_bas: ['9', '9', '9'],
    identifiant_saisie: `id-m${numero}`,
  }
}

const validation: ActeDuelEnFile = {
  type: 'validation',
  tournoi_id: 1,
  phase_id: 2,
  match_numero: 1,
  identifiant_saisie: 'id-v',
}

describe('rejouerActes', () => {
  it('rejoue les actes dans l’ordre (manches puis validation), une seule fois chacun', async () => {
    const envoyes: string[] = []
    const envoyer = vi.fn((a: ActeDuelEnFile) => {
      envoyes.push(a.identifiant_saisie)
      return Promise.resolve()
    })

    const res = await rejouerActes([manche(1), manche(2), validation], envoyer)

    expect(envoyes).toEqual(['id-m1', 'id-m2', 'id-v']) // ordre FIFO préservé
    expect(res.traites.map((a) => a.identifiant_saisie)).toEqual(['id-m1', 'id-m2', 'id-v'])
    expect(res.refuses).toEqual([])
    expect(res.interrompu).toBe(false)
  })

  it('s’arrête à la première panne réseau et garde le reste en file', async () => {
    const envoyer = vi.fn((a: ActeDuelEnFile) => {
      if (a.identifiant_saisie === 'id-m2') return Promise.reject(new TypeError('Failed to fetch'))
      return Promise.resolve()
    })

    const res = await rejouerActes([manche(1), manche(2), validation], envoyer)

    expect(res.traites.map((a) => a.identifiant_saisie)).toEqual(['id-m1'])
    expect(res.interrompu).toBe(true)
    expect(envoyer).toHaveBeenCalledTimes(2) // on n’a pas tenté la validation
  })

  it('retire un acte refusé DÉFINITIVEMENT (4xx métier, ex. duel_verrouille) et poursuit', async () => {
    const envoyer = vi.fn((a: ActeDuelEnFile) => {
      if (a.identifiant_saisie === 'id-m2') {
        return Promise.reject(new ErreurApi(422, 'duel_verrouille', 'Duel validé'))
      }
      return Promise.resolve()
    })

    const res = await rejouerActes([manche(1), manche(2), validation], envoyer)

    expect(res.traites.map((a) => a.identifiant_saisie)).toEqual(['id-m1', 'id-m2', 'id-v'])
    expect(res.refuses.map((a) => a.identifiant_saisie)).toEqual(['id-m2'])
    expect(res.interrompu).toBe(false)
  })

  it('GARDE en file un 409 duel_desynchronise (transitoire, le temps d’un re-seed)', async () => {
    const envoyer = vi.fn((a: ActeDuelEnFile) => {
      if (a.identifiant_saisie === 'id-m2') {
        return Promise.reject(new ErreurApi(409, 'duel_desynchronise', 'Classement changé'))
      }
      return Promise.resolve()
    })

    const res = await rejouerActes([manche(1), manche(2), validation], envoyer)

    expect(res.traites.map((a) => a.identifiant_saisie)).toEqual(['id-m1'])
    expect(res.refuses).toEqual([]) // pas définitif : rien à journaliser
    expect(res.interrompu).toBe(true) // arrêt → m2 et validation restent en file
  })

  it('GARDE en file un 401 (session scoreur perdue) — rejeu après reconnexion', async () => {
    const envoyer = vi.fn(() =>
      Promise.reject(new ErreurApi(401, 'non_authentifie', 'Non authentifié')),
    )

    const res = await rejouerActes([manche(1), validation], envoyer)

    expect(res.traites).toEqual([])
    expect(res.refuses).toEqual([])
    expect(res.interrompu).toBe(true)
    expect(envoyer).toHaveBeenCalledTimes(1)
  })

  it('SAUTE un acte superseded (retiré de la file par une saisie en ligne pendant le rejeu)', async () => {
    const envoyes: string[] = []
    const envoyer = vi.fn((a: ActeDuelEnFile) => {
      envoyes.push(a.identifiant_saisie)
      return Promise.resolve()
    })
    const estEncoreEnFile = (a: ActeDuelEnFile) => a.identifiant_saisie !== 'id-m2'

    const res = await rejouerActes([manche(1), manche(2), validation], envoyer, estEncoreEnFile)

    expect(envoyes).toEqual(['id-m1', 'id-v']) // m2 sautée
    expect(res.traites.map((a) => a.identifiant_saisie)).toEqual(['id-m1', 'id-v'])
    expect(res.interrompu).toBe(false)
  })

  // --- Correctif de revue E05US023 : un 409 ne gèle plus la tablette entière ------------------

  function mancheDe(matchNumero: number, numero: number): ActeDuelEnFile {
    return {
      ...manche(numero),
      match_numero: matchNumero,
      identifiant_saisie: `id-${matchNumero}-${numero}`,
    }
  }

  it('poursuit le drainage sur les AUTRES rencontres quand une rencontre est refusée en 409', async () => {
    // ⚠️ Le cas du jour J en poules : le `match_numero` court sur toute la phase, donc un archer
    // ajouté recompose les groupes et désynchronise définitivement les rencontres déjà tirées. Le
    // rejeu s'arrêtait au premier 409 et gardait TOUT en file — y compris les actes des rencontres
    // saines, qui n'avaient aucun problème. Une tablette ayant saisi pendant une coupure ne
    // synchronisait plus rien de la journée.
    const envoyes: string[] = []
    const envoyer = vi.fn((a: ActeDuelEnFile) => {
      envoyes.push(a.identifiant_saisie)
      if (a.match_numero === 1) {
        return Promise.reject(new ErreurApi(409, 'duel_desynchronise', 'désynchronisé'))
      }
      return Promise.resolve()
    })

    const res = await rejouerActes([mancheDe(1, 1), mancheDe(2, 1), mancheDe(3, 1)], envoyer)

    expect(envoyes).toEqual(['id-1-1', 'id-2-1', 'id-3-1'])
    expect(res.traites.map((a) => a.match_numero)).toEqual([2, 3])
    expect(res.refuses).toEqual([])
    expect(res.interrompu).toBe(true) // la rencontre 1 reste en file : rien n'est perdu
  })

  it('garde l’ordre AU SEIN d’une rencontre refusée : sa validation n’est pas envoyée', async () => {
    // L'ordre entre rencontres distinctes n'a aucune dépendance ; celui d'une même rencontre en a
    // une, et elle est stricte : valider suppose ses manches rejouées.
    const envoyes: string[] = []
    const envoyer = vi.fn((a: ActeDuelEnFile) => {
      envoyes.push(a.identifiant_saisie)
      if (a.match_numero === 1) {
        return Promise.reject(new ErreurApi(409, 'duel_desynchronise', 'désynchronisé'))
      }
      return Promise.resolve()
    })

    const res = await rejouerActes([mancheDe(1, 1), validation, mancheDe(2, 1)], envoyer)

    expect(envoyes).toEqual(['id-1-1', 'id-2-1']) // la validation de la rencontre 1 est sautée
    expect(res.traites.map((a) => a.identifiant_saisie)).toEqual(['id-2-1'])
    expect(res.interrompu).toBe(true)
  })

  it('s’arrête pour de bon sur une panne réseau, sans essayer les rencontres suivantes', async () => {
    // Une panne réseau n'est pas un refus : poursuivre ne ferait que collectionner des `fetch` qui
    // pendent. La distinction avec le 409 est tout l'objet du correctif.
    const envoyes: string[] = []
    const envoyer = vi.fn((a: ActeDuelEnFile) => {
      envoyes.push(a.identifiant_saisie)
      return Promise.reject(new TypeError('Failed to fetch'))
    })

    const res = await rejouerActes([mancheDe(1, 1), mancheDe(2, 1)], envoyer)

    expect(envoyes).toEqual(['id-1-1'])
    expect(res.traites).toEqual([])
    expect(res.interrompu).toBe(true)
  })
})
