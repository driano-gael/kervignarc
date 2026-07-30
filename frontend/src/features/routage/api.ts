// Accès API du panneau de routage (E04US018). Miroir des DTO de `api/v1/routage.py`.
//
// Portée `'aucune'` : c'est une **lecture publique** (contrat E10US001), et surtout la même donnée
// que liront les trois autres canaux de routage (`D-09` — appli publique E07US008, écran de salle
// E07US004). Le panneau s'affiche donc aussi bien sur la tablette (jeton de poste) que sur l'écran
// scoreur (jeton de scoreur), sans dépendre de l'identité qui le consulte.

import { fetchJson } from '../../shared/api/client'

export interface Duelliste {
  archer_id: number
  nom: string
  prenom: string
}

// Le prochain rendez-vous d'un archer. `cible`/`position` sont `null` au-delà du 1er tour (le
// placement intégral 1→N est E05US010) et `manque` dit alors pourquoi — on **nomme** l'attente
// plutôt que de laisser un blanc. `adversaire` est `null` tant que le duel amont n'est pas tranché,
// `sources_en_attente` en donnant alors le numéro.
export interface ProchainDuel {
  numero: number
  tour: number
  libelle: string
  cible: number | null
  position: string | null
  adversaire: Duelliste | null
  sources_en_attente: number[]
  manque: string | null
  // L'inverse de `manque` : la cible **est** là, mais le duel n'est pas côte à côte (plan matérialisé
  // sur un autre appariement, ou cibles trop petites). On affiche la cible **et** l'avertissement —
  // retirer une information juste ne rend service à personne.
  alerte: string | null
}

export type IssueRoutage = 'prochain_duel' | 'termine' | 'indisponible'

export interface RoutageArcher {
  archer_id: number
  nom: string
  prenom: string
  issue: IssueRoutage
  prochain: ProchainDuel | null
  rang_final: number | null
  tour_sortie: string | null
  motif: string | null
}

export interface Routage {
  phase_id: number | null
  archers: RoutageArcher[]
}

// `phaseId` omis = le serveur vise la première phase d'élimination directe du tournoi : la tablette
// de qualification ne connaît que sa cible et son départ, pas l'arbre. L'ordre des `archerIds` est
// **conservé** par le serveur — le panneau affiche A, B, C, D dans l'ordre de la grille.
export function getRoutage(
  tournoiId: number,
  archerIds: number[],
  phaseId?: number | null,
): Promise<Routage> {
  const parametres = new URLSearchParams()
  for (const archerId of archerIds) parametres.append('archer_id', String(archerId))
  if (phaseId != null) parametres.set('phase_id', String(phaseId))
  return fetchJson<Routage>(`/api/v1/routage/${tournoiId}?${parametres}`, undefined, 'aucune')
}
