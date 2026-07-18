// Accès API de la feature « catégories » (E01US003) : CRUD des catégories d'un tournoi.
// Miroir des DTO exposés par `api/v1/categories.py`.

import { fetchJson } from '../../shared/api/client'

export type SexeCategorie = 'H' | 'F' | 'mixte'

// Les huit tranches d'âge FFTA (E01US013) — vocabulaire **fermé**, miroir de l'enum `TrancheAge`
// du backend. Une catégorie couvre une ou plusieurs de ces tranches (`ages`).
export type TrancheAge = 'U11' | 'U13' | 'U15' | 'U18' | 'U21' | 'S1' | 'S2' | 'S3'

export interface Categorie {
  id: number
  tournoi_id: number
  libelle: string
  arme: string | null
  // Tranches d'âge éligibles (E01US013) : toujours un tableau (éventuellement vide), jamais un
  // scalaire. Les regroupements arc nu s'y lisent en clair (« U18 » → ['U15', 'U18']).
  ages: TrancheAge[]
  sexe: SexeCategorie | null
  // Blason par défaut (E01US006), facultatif : null = aucun.
  blason_id: number | null
  // Hauteur du centre de l'or, en cm (E03US001, ADR-0022) : pilote la contrainte de placement
  // « une butte, une seule hauteur ». Défaut FFTA 130 ; 110 pour les U11.
  hauteur_cm: number
}

export interface NouvelleCategorie {
  libelle: string
  arme?: string | null
  ages?: TrancheAge[]
  sexe?: SexeCategorie | null
  blason_id?: number | null
  // Le front l'envoie **toujours** : à l'édition, `hauteur_cm` est désormais **obligatoire**
  // (DETTE-009 résorbée — le serveur répond 400 si omis) ; à la création, il a un défaut serveur
  // (130) mais on le transmet aussi, par cohérence. `?` car le type est partagé création/édition.
  hauteur_cm?: number
}

// L'édition porte sur les mêmes champs que la création.
export type ModifierCategorie = NouvelleCategorie

export function getCategories(tournoiId: number): Promise<Categorie[]> {
  return fetchJson<Categorie[]>(`/api/v1/tournois/${tournoiId}/categories`)
}

export function creerCategorie(tournoiId: number, entree: NouvelleCategorie): Promise<Categorie> {
  return fetchJson<Categorie>(`/api/v1/tournois/${tournoiId}/categories`, {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function modifierCategorie(id: number, entree: ModifierCategorie): Promise<Categorie> {
  return fetchJson<Categorie>(`/api/v1/categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function supprimerCategorie(id: number): Promise<void> {
  return fetchJson<void>(`/api/v1/categories/${id}`, { method: 'DELETE' })
}

// Pré-charge le jeu de catégories FFTA salle (18 m) dans un tournoi (E01US004). Idempotent côté
// serveur (les libellés déjà présents sont ignorés) ; renvoie les catégories effectivement créées.
export function prechargerCategoriesFFTA(tournoiId: number): Promise<Categorie[]> {
  return fetchJson<Categorie[]>(`/api/v1/tournois/${tournoiId}/categories/precharger-ffta`, {
    method: 'POST',
  })
}
