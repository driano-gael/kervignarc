// Accès API de la feature « poste » (E04US001) : rattachement par code, relecture de cible,
// détachement. Miroir des DTO exposés par `api/v1/postes.py` (routes à la racine
// `/api/v1/postes/session`). Le code **seul** rattache (aucun tournoi à désigner : il est unique dans
// toute la base). Le jeton renvoyé est joint ensuite via l'en-tête `X-Jeton-Poste`.

import { fetchJson } from '../../shared/api/client'
import type { CiblePoste } from '../../shared/stores/sessionPosteStore'

export interface SessionPoste {
  jeton: string
  poste: CiblePoste
}

export function rattacherPoste(code: string): Promise<SessionPoste> {
  // Portée `'aucune'` : le rattachement est un login par code — aucun jeton joint (surtout pas le
  // Bearer admin, qui se ferait purger par un code erroné), et un refus (401 `code_poste_inconnu`,
  // ou 409 `rattachement_tournoi_termine`) n'expire aucune session existante.
  return fetchJson<SessionPoste>(
    '/api/v1/postes/session',
    { method: 'POST', body: JSON.stringify({ code }) },
    'aucune',
  )
}

export function cibleDuPoste(): Promise<CiblePoste> {
  // Portée `'poste'` : relit la cible du poste courant (réouverture / vérification de révocation).
  // Un 401 (tournoi terminé, serveur redémarré) purge la session de poste, jamais une autre.
  return fetchJson<CiblePoste>('/api/v1/postes/session', undefined, 'poste')
}

export function deconnexionPoste(): Promise<void> {
  // Portée `'poste'` : détache la tablette (en-tête `X-Jeton-Poste`).
  return fetchJson<void>('/api/v1/postes/session/deconnexion', { method: 'POST' }, 'poste')
}
