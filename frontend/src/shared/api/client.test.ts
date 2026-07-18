// Tests de `fetchJson` — **portée d'identité** (E10US003, correctif de revue).
//
// Garde-fou de non-régression du défaut trouvé en revue : `fetchJson` joignait **les deux** jetons à
// chaque requête et, sur un 401, purgeait **toute** session dont le jeton était présent — si bien
// qu'un login scoreur raté (ou une action scoreur rejetée) déconnectait l'**admin** connecté dans le
// même navigateur. Le correctif : une requête n'engage qu'**une** identité (`portee`), et un 401 ne
// purge que celle-là. Ces tests verrouillent ce contrat.

import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest'
import {
  enregistrerJetonAdmin,
  enregistrerJetonPoste,
  enregistrerJetonScoreur,
  enregistrerSurNonAutorise,
  enregistrerSurNonAutorisePoste,
  enregistrerSurNonAutoriseScoreur,
  fetchJson,
} from './client'

function reponse(statut: number, corps: unknown): Response {
  return {
    ok: statut >= 200 && statut < 300,
    status: statut,
    json: async () => corps,
  } as Response
}

let purgeAdmin: Mock<() => void>
let purgeScoreur: Mock<() => void>
let purgePoste: Mock<() => void>
let fetchMock: ReturnType<typeof vi.fn>

function entetesEnvoyees(): Record<string, string> {
  const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined
  return (init?.headers ?? {}) as Record<string, string>
}

beforeEach(() => {
  enregistrerJetonAdmin(() => 'JETON-ADMIN')
  enregistrerJetonScoreur(() => 'JETON-SCOREUR')
  enregistrerJetonPoste(() => 'JETON-POSTE')
  purgeAdmin = vi.fn<() => void>()
  purgeScoreur = vi.fn<() => void>()
  purgePoste = vi.fn<() => void>()
  enregistrerSurNonAutorise(purgeAdmin)
  enregistrerSurNonAutoriseScoreur(purgeScoreur)
  enregistrerSurNonAutorisePoste(purgePoste)
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('fetchJson — jeton joint selon la portée', () => {
  it("portée 'admin' (défaut) joint le Bearer admin, pas l'en-tête scoreur", async () => {
    fetchMock.mockResolvedValue(reponse(200, { ok: true }))
    await fetchJson('/api/v1/tournois')
    const entetes = entetesEnvoyees()
    expect(entetes.Authorization).toBe('Bearer JETON-ADMIN')
    expect(entetes['X-Jeton-Scoreur']).toBeUndefined()
  })

  it("portée 'scoreur' joint l'en-tête scoreur, pas le Bearer admin", async () => {
    fetchMock.mockResolvedValue(reponse(204, null))
    await fetchJson('/api/v1/scoreurs/session/deconnexion', { method: 'POST' }, 'scoreur')
    const entetes = entetesEnvoyees()
    expect(entetes['X-Jeton-Scoreur']).toBe('JETON-SCOREUR')
    expect(entetes.Authorization).toBeUndefined()
  })

  it("portée 'poste' joint l'en-tête poste, ni le Bearer admin ni l'en-tête scoreur", async () => {
    fetchMock.mockResolvedValue(reponse(200, { tournoi_id: 1, cible_index: 3 }))
    await fetchJson('/api/v1/postes/session', undefined, 'poste')
    const entetes = entetesEnvoyees()
    expect(entetes['X-Jeton-Poste']).toBe('JETON-POSTE')
    expect(entetes.Authorization).toBeUndefined()
    expect(entetes['X-Jeton-Scoreur']).toBeUndefined()
  })

  it("portée 'aucune' (login) ne joint aucun jeton de session", async () => {
    fetchMock.mockResolvedValue(reponse(200, { jeton: 'x' }))
    await fetchJson('/api/v1/scoreurs/session', { method: 'POST' }, 'aucune')
    const entetes = entetesEnvoyees()
    expect(entetes.Authorization).toBeUndefined()
    expect(entetes['X-Jeton-Scoreur']).toBeUndefined()
    expect(entetes['X-Jeton-Poste']).toBeUndefined()
  })
})

describe('fetchJson — un 401 ne purge que la session de la portée', () => {
  it("login refusé (portée 'aucune') ne purge aucune session — le cas du bug", async () => {
    fetchMock.mockResolvedValue(reponse(401, { code: 'code_scoreur_inconnu', message: 'x' }))
    await expect(
      fetchJson('/api/v1/scoreurs/session', { method: 'POST' }, 'aucune'),
    ).rejects.toMatchObject({ statut: 401 })
    expect(purgeAdmin).not.toHaveBeenCalled()
    expect(purgeScoreur).not.toHaveBeenCalled()
  })

  it("401 scoreur purge la session scoreur, JAMAIS l'admin", async () => {
    fetchMock.mockResolvedValue(reponse(401, { code: 'non_authentifie', message: 'x' }))
    await expect(
      fetchJson('/api/v1/scoreurs/session/deconnexion', { method: 'POST' }, 'scoreur'),
    ).rejects.toMatchObject({ statut: 401 })
    expect(purgeScoreur).toHaveBeenCalledTimes(1)
    expect(purgeAdmin).not.toHaveBeenCalled()
  })

  it('401 admin purge la session admin, jamais celle du scoreur', async () => {
    fetchMock.mockResolvedValue(reponse(401, { code: 'non_authentifie', message: 'x' }))
    await expect(fetchJson('/api/v1/tournois', { method: 'POST' })).rejects.toMatchObject({
      statut: 401,
    })
    expect(purgeAdmin).toHaveBeenCalledTimes(1)
    expect(purgeScoreur).not.toHaveBeenCalled()
  })

  it('401 poste (tournoi terminé) purge la session poste, ni admin ni scoreur', async () => {
    fetchMock.mockResolvedValue(reponse(401, { code: 'non_authentifie', message: 'x' }))
    await expect(fetchJson('/api/v1/postes/session', undefined, 'poste')).rejects.toMatchObject({
      statut: 401,
    })
    expect(purgePoste).toHaveBeenCalledTimes(1)
    expect(purgeAdmin).not.toHaveBeenCalled()
    expect(purgeScoreur).not.toHaveBeenCalled()
  })
})
