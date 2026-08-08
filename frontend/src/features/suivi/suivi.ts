// Logique pure de la feature « suivi » (E07US006) — extraite des composants pour rester testable en
// node, patron de `placement/planConsultation.ts`. Deux gestes : filtrer les archers par nom lors de
// la recherche, et retrouver la place (cible + position) d'un archer dans le plan d'un départ.

import type { Archer } from '../competition/api'
import type { Depart } from '../departs/api'
import type { PlanDeCibles } from '../placement/api'

// Normalise pour une comparaison tolérante aux accents et à la casse : « Rémy » se retrouve avec
// « remy ». NFD sépare la lettre de son diacritique, qu'on retire (`̀`–`ͯ`), puis minuscules.
function normaliser(texte: string): string {
  return texte.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

// Les critères de recherche de l'appli publique (E16US004) : un nom **et/ou** un club.
export interface CritereRecherche {
  requete: string
  /** `null` = tous clubs confondus. Ne se confond pas avec `Archer.club_id === null`, qui veut dire
   * « club encore **inconnu** » (ADR-0014) et n'appartient donc à aucun club filtré. */
  clubId: number | null
}

// Filtre les archers sur le nom/prénom (accent/casse-insensible) **et** sur le club (E16US004,
// questionnaire P01 : *« mettre un filtre de tri par club en plus dans la recherche »*).
//
// **Aucun critère → liste vide** : la recherche n'est pas un déversoir de tout l'annuaire (D-09,
// règle héritée d'E07US006). Mais un **club seul suffit** — c'est ce qui fait du club un filtre à
// part entière et non un simple raffinage d'une recherche déjà tapée.
export function rechercherArchers(archers: Archer[], critere: CritereRecherche): Archer[] {
  const q = normaliser(critere.requete)
  if (q === '' && critere.clubId === null) return []
  return archers.filter((a) => {
    if (critere.clubId !== null && a.club_id !== critere.clubId) return false
    if (q === '') return true
    return normaliser(a.nom).includes(q) || normaliser(a.prenom).includes(q)
  })
}

// Filtre les archers sur le seul nom — la recherche de la sidebar admin (E12US006), qui n'a pas de
// filtre par club. Délègue à `rechercherArchers` : deux implémentations du même geste divergeraient.
export function filtrerArchers(archers: Archer[], requete: string): Archer[] {
  return rechercherArchers(archers, { requete, clubId: null })
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

// Une ligne de la journée d'un archer : le créneau (départ + horaire) et sa place (cible + position).
export interface LigneJournee {
  departId: number
  numeroDepart: number
  horaire: string | null
  cible: number
  position: string
}

// Construit la journée d'un archer : pour chaque départ où il est **posé**, son créneau et sa place,
// triés par numéro de départ. On lit **les plans** (autorité du placement, ADR-0033) et **la liste des
// départs** (numéro/horaire) — deux surfaces publiques **sans donnée personnelle**. On n'utilise
// **pas** l'endpoint des inscriptions : son DTO porte `paye`/`montant_du_centimes`, qui ne doivent pas
// atteindre le navigateur d'un spectateur anonyme (règle 6, correctif de revue B/C1). Conséquence
// assumée : un archer inscrit mais **pas encore placé** n'apparaît sur aucune ligne — on ne connaît sa
// journée qu'une fois posé (avant, « pas encore placé »).
export function construireJournee(
  archerId: number,
  departs: Depart[],
  plansParDepart: Map<number, PlanDeCibles>,
): LigneJournee[] {
  const journee: LigneJournee[] = []
  for (const depart of [...departs].sort((a, b) => a.numero - b.numero)) {
    const plan = plansParDepart.get(depart.id)
    if (!plan) continue
    const place = placeDansPlan(plan, archerId)
    if (!place) continue
    journee.push({
      departId: depart.id,
      numeroDepart: depart.numero,
      horaire: depart.horaire,
      cible: place.cible,
      position: place.position,
    })
  }
  return journee
}

// Les départs où tire **au moins un** archer suivi (E16US004, récapitulatif de journée).
//
// ⚠️ **Les créneaux des archers, pas celui de la salle.** Un premier jet lisait `departDeSalle`,
// c'est-à-dire le départ que la salle est en train de tirer : dès le créneau de l'après-midi lancé,
// un archer du matin perdait **en silence** toute la section « duels » de son récapitulatif — ses
// volées de qualification restant affichées, puisqu'elles sont scopées au tournoi et non au départ.
// Un « récapitulatif de la journée » qui s'ampute à 15 h ne tient pas son CA.
//
// ⚠️ **La liste est bornée, et c'est le point** : on dérive des plans **déjà chargés**, donc sans
// requête supplémentaire, et l'on ne retient que les créneaux réellement concernés — un le plus
// souvent, deux quand on suit des archers de deux départs. Interroger « tous les départs du
// tournoi » aurait été plus simple et aurait **aggravé `# DETTE-031`** (chaque entrée est une
// reconstruction serveur complète) au lieu de la laisser où elle est.
//
// Rend `[]` tant que les plans ne sont pas chargés : aucune requête ne part, le récapitulatif se
// remplit au rendu suivant. C'est le même comportement que la carte elle-même, qui ne connaît la
// place d'un archer qu'une fois son plan lu.
export function departsDesArchersSuivis(
  archerIds: readonly number[],
  departs: Depart[],
  plansParDepart: Map<number, PlanDeCibles>,
): number[] {
  const ids = archerIds.flatMap((archerId) =>
    construireJournee(archerId, departs, plansParDepart).map((ligne) => ligne.departId),
  )
  return [...new Set(ids)]
}
