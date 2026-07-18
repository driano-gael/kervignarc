// Accès API de la feature « scoreur-session » (E10US003, volet **session** scoreur) : connexion
// par code, déconnexion. Miroir des DTO exposés par `api/v1/scoreurs.py` (routes à la racine
// `/api/v1/scoreurs/session`). Le code **seul** ouvre la session (aucun tournoi à désigner : il est
// unique dans toute la base). Le jeton renvoyé est joint ensuite via l'en-tête `X-Jeton-Scoreur`.

import { fetchJson } from '../../shared/api/client'
import type { ScoreurConnecte } from '../../shared/stores/sessionScoreurStore'

export interface SessionScoreur {
  jeton: string
  scoreur: ScoreurConnecte
}

export function connexionScoreur(code: string): Promise<SessionScoreur> {
  return fetchJson<SessionScoreur>('/api/v1/scoreurs/session', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}

export function deconnexionScoreur(): Promise<void> {
  return fetchJson<void>('/api/v1/scoreurs/session/deconnexion', { method: 'POST' })
}
