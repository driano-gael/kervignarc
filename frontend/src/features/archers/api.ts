// Accès API de la feature « archers » (E02US003) : administration des inscrits d'un tournoi.
// Miroir des DTO exposés par `api/v1/competition.py`.
//
// L'inscription elle-même (E02US002) reste dans la feature `competition`, où vit le formulaire
// de saisie au guichet. Ici, c'est la liste et sa correction après coup : lire, éditer,
// désinscrire.

import { fetchJson } from '../../shared/api/client'
import type { Archer } from '../competition/api'

// Réexporté plutôt que redéclaré : deux copies de ce type divergeraient au premier champ ajouté,
// et c'est le **même** DTO serveur qui alimente les deux features.
export type { Archer }

// Édition d'un archer (E02US003) — **remplacement total**, pas mise à jour partielle.
// `club_id: null` **détache** le club (retour à « club inconnu », ADR-0014) ; il ne veut jamais
// dire « laisse en l'état ».
export interface ModifierArcher {
  nom: string
  prenom: string
  categorie_id: number
  club_id: number | null
  // Confirmations de l'admin après un premier 409, une par signalement. `autoriser_homonyme` :
  // l'édition fait entrer l'archer dans l'identité d'un autre inscrit (ADR-0015).
  // `autoriser_changement_categorie` : elle change la catégorie d'un archer qui a déjà tiré.
  autoriser_homonyme?: boolean
  autoriser_changement_categorie?: boolean
}

export function getArchers(tournoiId: number): Promise<Archer[]> {
  return fetchJson<Archer[]>(`/api/v1/tournois/${tournoiId}/archers`)
}

export function modifierArcher(id: number, entree: ModifierArcher): Promise<Archer> {
  return fetchJson<Archer>(`/api/v1/archers/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

// `autoriserSuppressionEngage` : confirmation de l'admin après un refus `archer_engage` (409).
// Elle efface **aussi les scores et le placement** de l'archer. En **paramètre de requête** et non
// dans le corps (un DELETE n'en a pas) — divergence de forme prévue par ADR-0015.
//
// Ne sert **pas** à enregistrer un abandon : un archer qui arrête en cours d'épreuve devient un
// forfait tracé (E12US004), qui conserve ses résultats. Ici, on détruit.
export function supprimerArcher(id: number, autoriserSuppressionEngage = false): Promise<void> {
  const parametres = autoriserSuppressionEngage ? '?autoriser_suppression_engage=true' : ''
  return fetchJson<void>(`/api/v1/archers/${id}${parametres}`, { method: 'DELETE' })
}
