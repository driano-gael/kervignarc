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

// Réglage du handicap (E05US015) — **remplacement total des deux valeurs**, comme `ModifierArcher`
// et pour la même raison : `null` veut dire « remets à rien », jamais « n'y touche pas ». Retirer
// une surcharge (revenir au handicap officiel) doit être exprimable.
//
// Ressource **séparée** de l'édition d'état civil : un handicap se règle souvent en série, et le
// passer par le PUT total obligerait à renvoyer nom/prénom/catégorie à chaque ajustement — donc à
// écraser une correction faite entre-temps depuis un autre poste.
export interface DefinirHandicap {
  officiel: number | null
  surcharge: number | null
}

export function definirHandicap(id: number, entree: DefinirHandicap): Promise<Archer> {
  return fetchJson<Archer>(`/api/v1/archers/${id}/handicap`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function getArchers(tournoiId: number): Promise<Archer[]> {
  return fetchJson<Archer[]>(`/api/v1/tournois/${tournoiId}/archers`)
}

// Une paire de fiches rapprochées par la détection de doublons (E02US005). `niveau` vaut
// `'probable'` (doublon très vraisemblable) ou `'a_verifier'` (rapprochement approximatif à
// confirmer) ; `a` et `b` sont ordonnées par identifiant croissant (déterminisme d'affichage).
export interface Doublon {
  niveau: string
  a: Archer
  b: Archer
}

export function getDoublons(tournoiId: number): Promise<Doublon[]> {
  return fetchJson<Doublon[]>(`/api/v1/tournois/${tournoiId}/doublons`)
}

// Fusionne un doublon : la fiche `gagnantId` (maître) absorbe `perdantId` (inscriptions et scores
// repris, la fiche absorbée disparaît). Renvoie la fiche maître. Le serveur refuse (409) si les deux
// fiches ont déjà tiré (`fusion_archers_engages`) ou si la fusion est structurellement impossible
// (`fusion_impossible` : même fiche, tournois différents) — ce sont des refus fermes, sans drapeau.
export function fusionnerArchers(gagnantId: number, perdantId: number): Promise<Archer> {
  return fetchJson<Archer>(`/api/v1/archers/${gagnantId}/fusionner`, {
    method: 'POST',
    body: JSON.stringify({ perdant_id: perdantId }),
  })
}

export function modifierArcher(id: number, entree: ModifierArcher): Promise<Archer> {
  return fetchJson<Archer>(`/api/v1/archers/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

// `autoriserSuppressionEngage` : confirmation de l'admin après un signalement `archer_engage`
// (409). Elle efface **aussi les scores et le placement** de l'archer. En **paramètre de requête**
// et non dans le corps (un DELETE n'en a pas) — divergence de forme sanctionnée par ADR-0016. ⚠️ Ne
// sert **pas** à enregistrer un abandon : un archer qui arrête devient un forfait tracé (E04US015 /
// ADR-0050), qui conserve ses résultats ; ici on détruit. DETTE-007 : la confirmation est
// **aveugle**, elle ne rappelle pas le compte de flèches annoncé.
export function supprimerArcher(id: number, autoriserSuppressionEngage = false): Promise<void> {
  const parametres = autoriserSuppressionEngage ? '?autoriser_suppression_engage=true' : ''
  return fetchJson<void>(`/api/v1/archers/${id}${parametres}`, { method: 'DELETE' })
}
