// Accès API de la feature « scoreurs » (E10US003, volet **définition** admin) : CRUD des scoreurs
// d'un tournoi. Miroir des DTO exposés par `api/v1/scoreurs.py`. Routes **imbriquées sous le
// tournoi** (un scoreur appartient à un tournoi) : l'édition et la suppression portent le `tournoiId`.
// La lecture aussi est réservée à l'admin (la réponse porte les **codes**, des secrets à distribuer).

import { fetchJson } from '../../shared/api/client'

export interface Scoreur {
  id: number
  tournoi_id: number
  nom: string
  // Code individuel **généré par le serveur**, à imprimer et remettre au scoreur : c'est son sésame
  // de connexion (mode d'identité « la personne », D-13). Non modifiable (figé à la création).
  code: string
}

export interface NouveauScoreur {
  // Le nom seul : le code est généré côté serveur. L'édition ne porte que sur le nom (code figé).
  nom: string
}

export function getScoreurs(tournoiId: number): Promise<Scoreur[]> {
  return fetchJson<Scoreur[]>(`/api/v1/tournois/${tournoiId}/scoreurs`)
}

export function creerScoreur(tournoiId: number, entree: NouveauScoreur): Promise<Scoreur> {
  return fetchJson<Scoreur>(`/api/v1/tournois/${tournoiId}/scoreurs`, {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function modifierScoreur(
  tournoiId: number,
  scoreurId: number,
  entree: NouveauScoreur,
): Promise<Scoreur> {
  return fetchJson<Scoreur>(`/api/v1/tournois/${tournoiId}/scoreurs/${scoreurId}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function supprimerScoreur(tournoiId: number, scoreurId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/scoreurs/${scoreurId}`, {
    method: 'DELETE',
  })
}
