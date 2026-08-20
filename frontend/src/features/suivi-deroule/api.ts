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
import type { PorteeArret } from '../../shared/phases/arrets'
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
  portee: PorteeArret
  /** Toutes les phases que cet arrêt a mises en pause : ce que la relance rendra d'un seul geste. */
  phases_arretees: number[]
  /** L'instant (ISO 8601, UTC) où cet arrêt a éteint sa **première** phase — `null` si rien encore
   * (E05US034).
   *
   * ⚠️ **Un instant, pas une durée**, et le serveur ne peut pas faire autrement : la route est
   * pollée toutes les 10 s mais le rendu vit *entre* deux réponses, si bien qu'un « depuis 14 min »
   * calculé là-bas resterait à 14 pendant dix secondes de plus. La conversion vit dans
   * `shared/phases/relance.ts`, avec ses tests. */
  arrete_depuis: string | null
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

// --- Arrêts posés le jour J (E05US034, ADR-0092) -------------------------------------------------

/** Ce que la pose renvoie : le tour **résolu**, pas le relatif envoyé.
 *
 * C'est ce que l'organisateur doit pouvoir vérifier — « j'ai demandé dans 2 tours, ça coupe après
 * le tour 4 » —, et c'est ce qui rend la réponse comparable aux arrêts programmés affichés à côté. */
export interface ArretDeCirconstance {
  id: number
  phase_id: number
  apres_tour: number
  portee: PorteeArret
}

/**
 * Pose une pause **dans ce créneau seul**, comptée depuis le tour en cours.
 *
 * ⚠️ **La route est adressée par créneau et par phase, et c'est ce qui la distingue de l'atelier.**
 * Poser un arrêt à l'atelier édite le déroulé du **tournoi** (`PUT /tournois/{id}/deroule`), que
 * tous les créneaux rejouent (ADR-0076 §4). Ici on agit sur ce qui tire **maintenant** (§5) : le
 * créneau du soir ne saura rien de cette pause.
 *
 * `dansXTours` compte le tour **en cours** : « 1 » veut dire « celui-là finit, puis on s'arrête ».
 * La conversion en numéro absolu est faite par le serveur — le tour courant est une donnée serveur,
 * et un client qui le calculerait couperait au mauvais endroit dès qu'il aurait dix secondes de
 * retard.
 */
export function poserArretRelatif(
  departId: number,
  phaseId: number,
  dansXTours: number,
  portee: PorteeArret,
): Promise<ArretDeCirconstance> {
  return fetchJson<ArretDeCirconstance>(
    `/api/v1/departs/${departId}/phases/${phaseId}/arrets`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dans_x_tours: dansXTours, portee }),
    },
    'admin',
  )
}
