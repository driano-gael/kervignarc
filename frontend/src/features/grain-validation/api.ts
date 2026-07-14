// Accès API de la feature « grain de validation » (E01US015, `D-11`).
// Miroir des DTO exposés par `api/v1/grain_validation.py`. Ressource rattachée au tournoi : le
// grain est porté côté serveur par la phase de qualification (transparent pour le client).

import { fetchJson } from '../../shared/api/client'

// Les trois grains du domaine. `fin_de_duel` n'est pas proposé sur une qualification (le serveur
// le refuse) : il existe ici parce que le moteur (EPIC-05) introduira les phases à duels.
export type TypeGrain = 'fin_de_serie' | 'fin_de_duel' | 'toutes_les_n_volees'

export interface Grain {
  grain: TypeGrain
  // Cadence, uniquement pour `toutes_les_n_volees` ; `null` pour les grains de fin.
  n_volees: number | null
}

export interface DefinitionGrain {
  grain: TypeGrain
  n_volees?: number | null
}

// Le grain du tournoi, ou `null` si son barème n'est pas encore défini (pas de phase).
export function getGrainDuTournoi(tournoiId: number): Promise<Grain | null> {
  return fetchJson<Grain | null>(`/api/v1/tournois/${tournoiId}/grain-validation`)
}

// Définit le grain de validation de la qualification du tournoi.
export function definirGrain(tournoiId: number, entree: DefinitionGrain): Promise<Grain> {
  return fetchJson<Grain>(`/api/v1/tournois/${tournoiId}/grain-validation`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}
