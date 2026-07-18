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
  // Portée `'aucune'` : la connexion par code est un login — aucun jeton joint (surtout pas le
  // Bearer admin, qui, si un admin est connecté dans le même navigateur, se ferait purger par un
  // code scoreur erroné), et un refus (401 `code_scoreur_inconnu`) n'expire aucune session.
  return fetchJson<SessionScoreur>(
    '/api/v1/scoreurs/session',
    { method: 'POST', body: JSON.stringify({ code }) },
    'aucune',
  )
}

export function deconnexionScoreur(): Promise<void> {
  // Portée `'scoreur'` : action du scoreur (en-tête `X-Jeton-Scoreur`). Un 401 ne purge que la
  // session scoreur, jamais celle de l'admin.
  return fetchJson<void>('/api/v1/scoreurs/session/deconnexion', { method: 'POST' }, 'scoreur')
}
