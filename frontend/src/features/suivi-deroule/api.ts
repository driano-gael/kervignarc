// Accès API du **suivi du déroulé** (E07US004, ADR-0064) : le schéma à braquets d'une édition en
// cours, rempli par la réalité. Miroir des DTO de `api/v1/suivi_deroule.py`.
//
// **Lecture publique** (portée `'aucune'`), et ce n'est pas un oubli : les deux consommateurs sont
// le poste de pilotage (admin, qui a un jeton) et l'**écran de salle**, qui n'en a pas — c'est un
// poste public projeté dans un gymnase. Un endpoint gardé rendrait l'écran muet.
//
// La feature ne redéclare **ni** `Bloc` **ni** `AvancementBloc` : ils viennent de
// `shared/schema-braquets/modele`, la source unique du modèle de schéma côté front.

import { fetchJson } from '../../shared/api/client'
import type { AvancementBloc, Bloc } from '../../shared/schema-braquets/modele'

export interface SuiviDeroule {
  /** Le nombre d'archers engagés — l'équivalent live du « je simule à N archers » de l'atelier. */
  effectif: number
  /** L'ordre de la phase qui tourne, ou `null` si aucune n'est démarrée. */
  ordre_courant: number | null
  /** Le **dessin** — exactement la forme que l'atelier reçoit de son diagnostic. */
  blocs: Bloc[]
  /** Le **remplissage**, apparié aux blocs par `ordre`. */
  avancement: AvancementBloc[]
}

// ⚠️ **Le suivi est celui d'un créneau, pas du tournoi** (E01US025, ADR-0075) : un départ rejoue le
// tournoi en entier, avec son effectif et son avancement propres. La route était
// `/tournois/{id}/suivi-deroule` et fusionnait les créneaux — déroulé dessiné en double, avancement
// du dernier créneau écrasant les autres, et tableaux dimensionnés sur la somme des inscrits.
export function getSuiviDeroule(departId: number): Promise<SuiviDeroule> {
  return fetchJson<SuiviDeroule>(`/api/v1/departs/${departId}/suivi-deroule`, undefined, 'aucune')
}

// --- Arrêts programmés : la relance (E05US033, ADR-0091) ----------------------------------------
//
// ⚠️ **Portée `'admin'`, à la différence du suivi ci-dessus.** Le suivi est public parce que l'écran
// de salle n'a pas de jeton ; relancer la salle est au contraire un **geste d'organisateur**, gardé
// par `exiger_admin` côté serveur. Les deux vivent dans le même module de feature parce qu'ils
// s'affichent au même endroit, pas parce qu'ils ont la même audience.

/** Un arrêt **franchi** qui attend un geste, miroir d'`ArretFranchiReponse`. */
export interface ArretEnAttente {
  id: number
  /** La phase **déclenchante** — celle dont le tour s'est achevé, pas forcément la seule arrêtée. */
  phase_id: number
  apres_tour: number
  portee: 'phase' | 'depart'
  /** Toutes les phases que cet arrêt a mises en pause : ce que la relance rendra d'un seul geste. */
  phases_arretees: number[]
}

export function getArretsEnAttente(departId: number): Promise<ArretEnAttente[]> {
  return fetchJson<ArretEnAttente[]>(
    `/api/v1/departs/${departId}/arrets/en-attente`,
    undefined,
    'admin',
  )
}

/** Relance la salle. Rend les identifiants des phases effectivement reparties. */
export function relancerArret(departId: number, arretId: number): Promise<number[]> {
  return fetchJson<number[]>(
    `/api/v1/departs/${departId}/arrets/${arretId}/relancer`,
    { method: 'POST' },
    'admin',
  )
}
