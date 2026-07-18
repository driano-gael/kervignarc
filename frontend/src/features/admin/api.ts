// Accès API de la feature « admin » (E10US002) : état de l'accès, définition au 1ᵉʳ usage,
// connexion, déconnexion. Miroir des DTO exposés par `api/v1/auth.py`.

import { fetchJson } from '../../shared/api/client'

export interface EtatAuth {
  // `false` → aucun accès admin défini (1ᵉʳ usage : proposer de le définir) ; `true` → se connecter.
  configure: boolean
}

export interface Identifiants {
  login: string
  mot_de_passe: string
}

export interface Jeton {
  jeton: string
}

export function getEtatAuth(): Promise<EtatAuth> {
  return fetchJson<EtatAuth>('/api/v1/auth/etat')
}

export function configurerAdmin(identifiants: Identifiants): Promise<Jeton> {
  // Portée `'aucune'` : un login ne joint aucun jeton de session existant et un refus (401) n'expire
  // aucune session (il n'y en a pas encore) — il ne doit rien purger.
  return fetchJson<Jeton>(
    '/api/v1/auth/configurer',
    { method: 'POST', body: JSON.stringify(identifiants) },
    'aucune',
  )
}

export function connexionAdmin(identifiants: Identifiants): Promise<Jeton> {
  return fetchJson<Jeton>(
    '/api/v1/auth/connexion',
    { method: 'POST', body: JSON.stringify(identifiants) },
    'aucune',
  )
}

export function deconnexionAdmin(): Promise<void> {
  return fetchJson<void>('/api/v1/auth/deconnexion', { method: 'POST' })
}
