// Accès API de la feature « barème de qualification » (E01US009).
// Miroir des DTO exposés par `api/v1/bareme_qualification.py`. Ressource rattachée au tournoi :
// le barème est porté côté serveur par la phase de qualification (transparent pour le client).

import { fetchJson } from '../../shared/api/client'

export interface Bareme {
  nb_volees: number
  nb_fleches_par_volee: number
  // Dérivés côté serveur : nb total de flèches et score maximum (toutes les flèches au max).
  nb_fleches_total: number
  score_max: number
}

export interface DefinitionBareme {
  nb_volees: number
  nb_fleches_par_volee: number
}

// Le barème du tournoi, ou `null` s'il n'est pas encore défini.
export function getBaremeDuTournoi(tournoiId: number): Promise<Bareme | null> {
  return fetchJson<Bareme | null>(`/api/v1/tournois/${tournoiId}/bareme-qualification`)
}

// Définit (crée ou met à jour) le barème de qualification du tournoi.
export function definirBareme(tournoiId: number, entree: DefinitionBareme): Promise<Bareme> {
  return fetchJson<Bareme>(`/api/v1/tournois/${tournoiId}/bareme-qualification`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}
