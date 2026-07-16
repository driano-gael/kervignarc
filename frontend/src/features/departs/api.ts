// Accès API de la feature « departs » (E02US004, ADR-0017) : CRUD des départs (créneaux) d'un
// tournoi. Miroir des DTO exposés par `api/v1/departs.py`. Routes **imbriquées sous le tournoi**
// (un départ n'existe pas hors de lui) : l'édition et la suppression portent donc le `tournoiId`.

import { fetchJson } from '../../shared/api/client'

export interface Depart {
  id: number
  tournoi_id: number
  numero: number
  // Libellé de créneau (ex. « 9h00 »), facultatif : `null` s'il n'a pas été précisé.
  horaire: string | null
  // Prix du créneau, en **centimes entiers** (ADR-0012) — l'unité est dans le nom. Obligatoire ;
  // `0` = gratuit. Voir `../competition/format` pour la mise en forme.
  tarif_centimes: number
}

export interface NouveauDepart {
  tarif_centimes: number
  horaire?: string | null
}

// L'édition porte sur les mêmes champs que la création (le numéro est fixe, attribué par le serveur).
export type ModifierDepart = NouveauDepart

export function getDeparts(tournoiId: number): Promise<Depart[]> {
  return fetchJson<Depart[]>(`/api/v1/tournois/${tournoiId}/departs`)
}

export function creerDepart(tournoiId: number, entree: NouveauDepart): Promise<Depart> {
  return fetchJson<Depart>(`/api/v1/tournois/${tournoiId}/departs`, {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function modifierDepart(
  tournoiId: number,
  departId: number,
  entree: ModifierDepart,
): Promise<Depart> {
  return fetchJson<Depart>(`/api/v1/tournois/${tournoiId}/departs/${departId}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function supprimerDepart(tournoiId: number, departId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/departs/${departId}`, { method: 'DELETE' })
}
