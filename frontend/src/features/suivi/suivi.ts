// Logique pure de la feature « suivi » (E07US006) — extraite des composants pour rester testable en
// node, patron de `placement/planConsultation.ts`. Deux gestes : filtrer les archers par nom lors de
// la recherche, et retrouver la place (cible + position) d'un archer dans le plan d'un départ.

import type { Archer } from '../competition/api'
import type { PlanDeCibles } from '../placement/api'

// Normalise pour une comparaison tolérante aux accents et à la casse : « Rémy » se retrouve avec
// « remy ». NFD sépare la lettre de son diacritique, qu'on retire (`̀`–`ͯ`), puis minuscules.
function normaliser(texte: string): string {
  return texte.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

// Filtre les archers dont le nom ou le prénom contient la requête (accent/casse-insensible). Une
// requête **vide** renvoie une liste **vide** : la recherche n'est pas un déversoir de tout l'annuaire
// — tant qu'on n'a rien tapé, on ne propose rien (D-09 : la recherche est l'exception, pas la porte).
export function filtrerArchers(archers: Archer[], requete: string): Archer[] {
  const q = normaliser(requete)
  if (q === '') return []
  return archers.filter((a) => normaliser(a.nom).includes(q) || normaliser(a.prenom).includes(q))
}

// La place d'un archer sur un départ : sa cible (rang de salle) et sa position (« A »…« D »).
export interface PlaceArcher {
  cible: number
  position: string
}

// Retrouve la place d'un archer dans le plan d'un départ, ou `null` s'il n'y est pas encore posé
// (réserve, ou plan pas encore généré). On lit le **plan du départ** plutôt que le champ `cible` de
// l'archer : ce dernier est unique alors qu'un archer peut tirer sur plusieurs créneaux — seul le plan
// par départ tranche sans ambiguïté « où, sur CE départ ».
export function placeDansPlan(plan: PlanDeCibles, archerId: number): PlaceArcher | null {
  for (const cible of plan.cibles) {
    const place = cible.placements.find((p) => p.archer_id === archerId)
    if (place) return { cible: cible.index, position: place.position }
  }
  return null
}
