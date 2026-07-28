// Accès API de la feature « jeu d'essai » (E15US001) : peupler un tournoi & instancier des scénarios.
// Miroir des DTO exposés par `api/v1/jeu_essai.py`. Outil **admin** de démo/QA : les appels partent
// avec le jeton admin (joint par le client). C'est de la **donnée réelle** persistée.

import { fetchJson } from '../../shared/api/client'

// Un scénario du catalogue, tel que présenté à l'écran (le prédicat de sélection reste côté serveur).
export interface Scenario {
  id: string
  libelle: string
  description: string
  nombre_archers: number
  nombre_departs: number
}

export interface BilanPeuplement {
  tournoi_id: number
  nombre_archers_crees: number
}

export interface ResultatScenario {
  tournoi_id: number
  nom: string
  nombre_archers: number
  nombre_departs: number
}

export function getScenarios(): Promise<Scenario[]> {
  return fetchJson<Scenario[]>('/api/v1/jeu-essai/scenarios')
}

// Peuple un tournoi **existant** de `nombre` archers de test. `graine` optionnelle : absente, le
// serveur utilise une graine stable (jeu rejouable, règle 9).
export function peuplerTournoi(
  tournoiId: number,
  nombre: number,
  graine?: number,
): Promise<BilanPeuplement> {
  return fetchJson<BilanPeuplement>(`/api/v1/tournois/${tournoiId}/jeu-essai/peupler`, {
    method: 'POST',
    body: JSON.stringify({ nombre, graine: graine ?? null }),
  })
}

// Instancie un scénario en un tournoi **complet, prêt à lancer** ; renvoie le tournoi créé.
export function instancierScenario(scenarioId: string, graine?: number): Promise<ResultatScenario> {
  return fetchJson<ResultatScenario>(`/api/v1/jeu-essai/scenarios/${scenarioId}/instancier`, {
    method: 'POST',
    body: JSON.stringify({ graine: graine ?? null }),
  })
}
