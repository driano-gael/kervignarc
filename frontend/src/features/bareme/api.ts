// Accès API de la feature « barème de qualification » (E01US009).
// Miroir des DTO exposés par `api/v1/bareme_qualification.py`. Ressource rattachée au tournoi :
// le barème est porté côté serveur par la phase de qualification (transparent pour le client).

import { fetchJson } from '../../shared/api/client'
import type { TypeGrain } from '../grain-validation/api'

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

// --- E05US025 : plusieurs qualifications dans un même déroulé (ADR-0082) ------------------------
//
// Miroir de `QualificationReponse`. « Le barème du tournoi » n'existe plus en général : un déroulé
// peut enchaîner 3x20 puis une haute et une basse à 3x15, chacune avec ses réglages. Les fonctions
// ci-dessus restent pour le **premier** réglage d'un tournoi neuf, dont le déroulé est vide — c'est
// le seul chemin qui *crée* une qualification.

export interface Qualification {
  etape_id: number
  ordre: number
  // Libellé calculé par le serveur (« Qualification 1 », « Qualification 2 »…) : le vocabulaire
  // métier n'a qu'un domicile, et le front n'a pas à réinventer une numérotation.
  libelle: string
  bareme: Bareme | null
  // Typé plutôt que `string` : l'écran de grain lit ces deux champs, et un `as TypeGrain` à
  // l'usage serait un cast non justifié là où le serveur rend déjà une valeur close.
  grain: TypeGrain | null
  grain_n_volees: number | null
}

// Les qualifications du déroulé, dans l'ordre de la séquence (liste vide si aucune).
export function getQualifications(tournoiId: number): Promise<Qualification[]> {
  return fetchJson<Qualification[]>(`/api/v1/tournois/${tournoiId}/qualifications`)
}

// Règle le barème d'une qualification désignée. Ne crée rien : l'étape est composée à l'atelier.
export function definirBaremeEtape(
  tournoiId: number,
  etapeId: number,
  entree: DefinitionBareme,
): Promise<Bareme> {
  return fetchJson<Bareme>(`/api/v1/tournois/${tournoiId}/qualifications/${etapeId}/bareme`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}
