// Accès API de la feature « équipes » (E13US002) : composition des équipes d'un tournoi.
// Miroir des DTO exposés par `api/v1/equipes.py` ; routes admin imbriquées sous le tournoi.

import { fetchJson } from '../../shared/api/client'

export type TypeEquipe = 'standard' | 'mixte'

// Codes d'écart renvoyés par le serveur : jamais affichés bruts, cf. `libelleEcart` (`presentation.ts`).
export type EcartEquipe =
  | 'effectif_insuffisant'
  | 'effectif_excedentaire'
  | 'armes_differentes'
  | 'arme_non_verifiable'
  | 'mixite_manquante'
  | 'sexes_differents'
  | 'sexe_non_verifiable'

export interface MembreEquipe {
  archer_id: number
  nom: string
  prenom: string
  categorie: string
}

export interface Equipe {
  id: number
  tournoi_id: number
  nom: string
  type: TypeEquipe
  effectif_attendu: number
  membres: MembreEquipe[]
  conforme: boolean
  ecarts: EcartEquipe[]
}

export interface EntreeEquipe {
  nom: string
  type: TypeEquipe
  effectif_attendu: number | null
}

const base = (tournoiId: number) => `/api/v1/tournois/${tournoiId}/equipes`

export function getEquipes(tournoiId: number): Promise<Equipe[]> {
  return fetchJson<Equipe[]>(base(tournoiId))
}

export function creerEquipe(tournoiId: number, entree: EntreeEquipe): Promise<Equipe> {
  return fetchJson<Equipe>(base(tournoiId), { method: 'POST', body: JSON.stringify(entree) })
}

export function modifierEquipe(
  tournoiId: number,
  equipeId: number,
  entree: EntreeEquipe,
): Promise<Equipe> {
  return fetchJson<Equipe>(`${base(tournoiId)}/${equipeId}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function supprimerEquipe(tournoiId: number, equipeId: number): Promise<void> {
  return fetchJson<void>(`${base(tournoiId)}/${equipeId}`, { method: 'DELETE' })
}

export function ajouterMembre(
  tournoiId: number,
  equipeId: number,
  archerId: number,
): Promise<Equipe> {
  return fetchJson<Equipe>(`${base(tournoiId)}/${equipeId}/membres`, {
    method: 'POST',
    body: JSON.stringify({ archer_id: archerId }),
  })
}

export function retirerMembre(
  tournoiId: number,
  equipeId: number,
  archerId: number,
): Promise<Equipe> {
  return fetchJson<Equipe>(`${base(tournoiId)}/${equipeId}/membres/${archerId}`, {
    method: 'DELETE',
  })
}
