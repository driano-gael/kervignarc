// Tests de `rejouer` (E04US009, ADR-0037) — rejeu de la file hors-ligne. On stube l'envoi (comme
// `client.test` stube `fetch`) : succès, panne réseau (le `fetch` rejette), refus serveur
// (`ErreurApi`). Le zéro-doublon lui-même est garanti côté serveur (idempotence, ADR-0036) ; ici on
// vérifie l'**ordre**, l'**arrêt** sur panne, et le **retrait** des refus définitifs.

import { describe, expect, it, vi } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import type { VoleeEnFile } from '../../shared/stores/fileHorsLigneStore'
import { rejouer } from './rejeu'

function corps(numero: number): VoleeEnFile {
  return {
    tournoi_id: 1,
    archer_id: 7,
    numero,
    valeurs: ['10', '9', '9'],
    saisie_par: 'DURAND',
    identifiant_saisie: `id-${numero}`,
  }
}

describe('rejouer', () => {
  it('renvoie toutes les saisies dans l’ordre, une seule fois chacune', async () => {
    const envoyees: number[] = []
    const envoyer = vi.fn((c: VoleeEnFile) => {
      envoyees.push(c.numero)
      return Promise.resolve()
    })

    const res = await rejouer([corps(1), corps(2), corps(3)], envoyer)

    expect(envoyees).toEqual([1, 2, 3]) // ordre FIFO préservé
    expect(envoyer).toHaveBeenCalledTimes(3) // pas de renvoi en double
    expect(res.traitees.map((c) => c.numero)).toEqual([1, 2, 3])
    expect(res.refusees).toEqual([])
    expect(res.interrompu).toBe(false)
  })

  it('s’arrête à la première panne réseau et garde le reste en file', async () => {
    const envoyer = vi.fn((c: VoleeEnFile) => {
      if (c.numero === 2) return Promise.reject(new TypeError('Failed to fetch'))
      return Promise.resolve()
    })

    const res = await rejouer([corps(1), corps(2), corps(3)], envoyer)

    expect(res.traitees.map((c) => c.numero)).toEqual([1]) // seule la 1 est passée
    expect(res.interrompu).toBe(true)
    expect(envoyer).toHaveBeenCalledTimes(2) // on n’a même pas tenté la 3
  })

  it('retire une saisie refusée DÉFINITIVEMENT par le serveur (4xx métier) et poursuit', async () => {
    const envoyer = vi.fn((c: VoleeEnFile) => {
      if (c.numero === 2) {
        return Promise.reject(new ErreurApi(404, 'blason_introuvable', 'Blason introuvable'))
      }
      return Promise.resolve()
    })

    const res = await rejouer([corps(1), corps(2), corps(3)], envoyer)

    expect(res.traitees.map((c) => c.numero)).toEqual([1, 2, 3]) // les 3 retirées de la file
    expect(res.refusees.map((c) => c.numero)).toEqual([2]) // la 2 est un refus à journaliser
    expect(res.interrompu).toBe(false)
  })

  it('GARDE en file un refus TRANSITOIRE (5xx, serveur saturé) — ne rien perdre', async () => {
    // Cas « troupeau tonitruant » : 30 tablettes rejouent, le writer unique renvoie un 503.
    const envoyer = vi.fn((c: VoleeEnFile) => {
      if (c.numero === 2) {
        return Promise.reject(new ErreurApi(503, 'indisponible', 'Service indisponible'))
      }
      return Promise.resolve()
    })

    const res = await rejouer([corps(1), corps(2), corps(3)], envoyer)

    expect(res.traitees.map((c) => c.numero)).toEqual([1]) // seule la 1 est passée
    expect(res.refusees).toEqual([]) // la 2 n'est PAS un refus définitif : rien à journaliser
    expect(res.interrompu).toBe(true) // on s'arrête → 2 et 3 restent en file pour un rejeu ultérieur
    expect(envoyer).toHaveBeenCalledTimes(2) // on n'a pas tenté la 3
  })

  it('GARDE en file un 401 (serveur redémarré, jeton de poste perdu) — rejeu après re-rattachement', async () => {
    const envoyer = vi.fn(() =>
      Promise.reject(new ErreurApi(401, 'non_authentifie', 'Non authentifié')),
    )

    const res = await rejouer([corps(1), corps(2)], envoyer)

    expect(res.traitees).toEqual([]) // rien retiré : les scores ne sont pas perdus
    expect(res.refusees).toEqual([])
    expect(res.interrompu).toBe(true)
    expect(envoyer).toHaveBeenCalledTimes(1) // arrêt dès le premier 401
  })

  it('SAUTE une volée superseded (retirée de la file par une saisie en ligne pendant le rejeu)', async () => {
    const envoyees: number[] = []
    const envoyer = vi.fn((c: VoleeEnFile) => {
      envoyees.push(c.numero)
      return Promise.resolve()
    })
    // La volée 2 a été retirée entre-temps (corrigée en ligne) → ne doit PAS être renvoyée : son vieux
    // corps écraserait la valeur neuve côté serveur (dernier-écrit-gagne par numéro).
    const estEncoreEnFile = (c: VoleeEnFile) => c.numero !== 2

    const res = await rejouer([corps(1), corps(2), corps(3)], envoyer, estEncoreEnFile)

    expect(envoyees).toEqual([1, 3]) // la 2 sautée
    expect(res.traitees.map((c) => c.numero)).toEqual([1, 3]) // la 2 n'est pas « traitée »
    expect(res.interrompu).toBe(false)
  })
})
