// Accès API de la feature « placement » (E03US004, ADR-0024) : ajustement manuel du plan de cibles
// d'un départ. Miroir des DTO exposés par `api/v1/placement.py`.
//
// Le plan associe des **inscriptions** à des positions de cibles. La lecture renvoie le plan
// **persisté** (jamais recalculé à la volée) : cibles remplies + réserve (les `conflits`). Les
// écritures — régénérer/annuler, déplacer/échanger/mettre en réserve, placer les restants — sont
// réservées à l'admin côté serveur et renvoient le plan à jour.

import { fetchJson } from '../../shared/api/client'

// Pourquoi un archer est en réserve (non posé) : `sans_blason` (aucun blason pour tirer),
// `non_place` (aucune cible ne peut l'accueillir), `cloisonnement` (c'est le **réglage** de
// cloisonnement, et non la salle, qui l'exclut — E03US007), `en_reserve` (en attente d'un
// placement). Vocabulaire **fermé**, miroir de l'enum `RaisonConflit` du domaine.
export type RaisonConflit = 'sans_blason' | 'non_place' | 'cloisonnement' | 'en_reserve'

// Ce qu'une cible n'a pas le droit de mêler (E03US007, RG-4) — réglage **du tournoi**, à quatre
// positions. `aucun` = comportement d'origine. `categorie` sépare les catégories, `blason` les
// blasons (deux catégories tirant le même carton restent alors ensemble), `blason_et_categorie`
// les deux.
export type Cloisonnement = 'aucun' | 'categorie' | 'blason' | 'blason_et_categorie'

// Un archer posé sur une cible : sa position (lettre « A »…« D »), le blason sur lequel il tire, et
// son `inscription_id` — la cible du `PUT` de déplacement (l'archer sur *ce* départ). Le serveur
// l'expose directement pour éviter au client de reconstituer la correspondance archer → inscription.
export interface Placement {
  position: string
  archer_id: number
  blason_id: number
  inscription_id: number
}

// Une cible du plan : son rang (`index`), son plafond d'archers (`capacite`) et les archers posés
// (`placements`, vide si la cible est libre).
//
// `mixite_non_garantie` (RG-3, E03US006) : `true` quand la cible porte ≥ 2 archers sans qu'on puisse
// affirmer ≥ 2 clubs distincts (un seul club, ou clubs inconnus — le serveur traite `NULL` comme
// *indécidable*). L'admin le voit pour ajuster à la main s'il le souhaite ; ce n'est **pas** une
// erreur, juste un objectif d'équité non atteint. Recalculé serveur à chaque lecture (jamais persisté).
//
// `cloisonnement_non_respecte` (E03US007) : `true` quand la cible **mêle** ce que le réglage du
// tournoi interdit de mêler. Le placement auto ne peut pas produire ça (contrainte dure) : c'est le
// signe d'un plan **posé avant** l'activation du réglage, donc à régénérer.
export interface CiblePlacee {
  index: number
  capacite: number
  placements: Placement[]
  mixite_non_garantie: boolean
  cloisonnement_non_respecte: boolean
}

// Un archer que le placement n'a pas pu poser (il est **dans la réserve**), et pourquoi. Porte aussi
// son `inscription_id` : pour le reposer par glisser-déposer depuis la réserve.
export interface Conflit {
  archer_id: number
  raison: RaisonConflit
  inscription_id: number
}

export interface PlanDeCibles {
  depart_id: number
  cibles: CiblePlacee[]
  conflits: Conflit[]
}

// Gravité d'une régénération (E12US007, ADR-0040), miroir de `NiveauImpact` du domaine : `aucun`
// (rien de placé → pas d'alerte), `confirmation` (placés, sans score → confirmation simple),
// `massif` (des scores existent → taper un mot).
export type NiveauImpact = 'aucun' | 'confirmation' | 'massif'

// Impact chiffré de régénérer le plan d'un départ, prévisualisé **avant** d'agir. `cibles_avec_scores`
// = cibles dont un archer a déjà des scores (ils seront **conservés**, mais leur présence rend
// l'action massive).
export interface ImpactRegeneration {
  niveau: NiveauImpact
  archers_deplaces: number
  cibles_avec_scores: number
}

// Destination d'un déplacement : une case (`cible_index` + `position`) ou la **réserve**
// (`cible_index: null`). Une case libre déplace ; une case occupée échange atomiquement.
export interface Destination {
  cible_index: number | null
  position: string | null
}

// Réglage de cloisonnement du tournoi (E03US007). Lecture ouverte ; écriture réservée à l'admin
// côté serveur. Le PUT **ne replace personne** : il vaut pour la prochaine génération, les
// déplacements manuels et les badges — d'où l'invalidation du plan côté hook.
export function getCloisonnement(tournoiId: number): Promise<{ cloisonnement: Cloisonnement }> {
  return fetchJson<{ cloisonnement: Cloisonnement }>(`/api/v1/tournois/${tournoiId}/cloisonnement`)
}

export function reglerCloisonnement(
  tournoiId: number,
  cloisonnement: Cloisonnement,
): Promise<{ cloisonnement: Cloisonnement }> {
  return fetchJson<{ cloisonnement: Cloisonnement }>(
    `/api/v1/tournois/${tournoiId}/cloisonnement`,
    {
      method: 'PUT',
      body: JSON.stringify({ cloisonnement }),
    },
  )
}

const basePlan = (tournoiId: number, departId: number) =>
  `/api/v1/tournois/${tournoiId}/departs/${departId}/plan-de-cibles`

export function getPlanDeCibles(tournoiId: number, departId: number): Promise<PlanDeCibles> {
  return fetchJson<PlanDeCibles>(basePlan(tournoiId, departId))
}

// Prévisualise l'impact de régénérer le plan (E12US007) : lecture pure, sans rien écrire. Le front
// s'en sert pour afficher l'alerte chiffrée **avant** d'agir.
export function getImpactRegeneration(
  tournoiId: number,
  departId: number,
): Promise<ImpactRegeneration> {
  return fetchJson<ImpactRegeneration>(`${basePlan(tournoiId, departId)}/impact-regeneration`)
}

// Régénère le plan auto (déterministe). Sert **aussi** à « annuler les modifications » : l'auto
// écrase les ajustements manuels (ADR-0024). `confirme` autorise l'écrasement d'un plan **massif**
// (des scores existent, E12US007) ; sans lui, un plan massif renvoie 409 `replacement_non_confirme`.
export function regenererPlan(
  tournoiId: number,
  departId: number,
  confirme = false,
): Promise<PlanDeCibles> {
  return fetchJson<PlanDeCibles>(`${basePlan(tournoiId, departId)}/regenerer`, {
    method: 'POST',
    body: JSON.stringify({ confirme }),
  })
}

// Déplace / échange / met en réserve un inscrit. `409 deplacement_invalide` si le geste viole une
// contrainte (état serveur **inchangé**) : le client affiche le message et refetch le plan.
export function deplacerInscription(
  tournoiId: number,
  departId: number,
  inscriptionId: number,
  destination: Destination,
): Promise<PlanDeCibles> {
  return fetchJson<PlanDeCibles>(`${basePlan(tournoiId, departId)}/inscriptions/${inscriptionId}`, {
    method: 'PUT',
    body: JSON.stringify(destination),
  })
}

// Place automatiquement la réserve dans les trous du plan. Les archers qu'aucune cible ne peut
// prendre (sans blason, hauteur incompatible) restent en réserve.
export function placerRestants(tournoiId: number, departId: number): Promise<PlanDeCibles> {
  return fetchJson<PlanDeCibles>(`${basePlan(tournoiId, departId)}/placer-restants`, {
    method: 'POST',
  })
}
