// Le modèle du **schéma à braquets** — partagé par les trois surfaces (E01US024, E07US004).
//
// Ces types décrivent ce qu'une **projection de déroulé** contient : les blocs (une phase chacun),
// les flèches (un prélèvement chacune), les braquets (un tour chacun). Ils sont identiques d'un bout
// à l'autre parce que le serveur rend la même chose au diagnostic d'atelier
// (`GET /api/v1/formats/{id}/diagnostic`) et au suivi d'une édition
// (`GET /api/v1/tournois/{id}/suivi-deroule`) — c'est la contrainte du CA d'E07US004 : *« le **même**
// schéma à braquets que l'atelier, mais rempli par la réalité »*.
//
// Ils vivent en `shared/` et non dans `features/deroule/` parce qu'ils sont désormais consommés par
// trois features (atelier, pilotage, écran de salle) : un type partagé qui habite chez l'un de ses
// consommateurs fait dépendre les deux autres d'une feature qui ne les concerne pas.

import type { IssueTour, NatureSource, TypePhase } from '../phases/catalogue'

// Ce qu'une anomalie empêche (ADR-0063 §3). `bloquante` : le défaut est vrai quel que soit
// l'effectif, le format ne peut pas servir un tournoi. `avertissement` : il n'est vrai qu'à
// **cet** effectif — le format n'est pas faux, il ne tient pas ici.
export type Gravite = 'bloquante' | 'avertissement'

// Un défaut du déroulé, **localisé** : `ordre` désigne le bloc du schéma auquel le coller
// (`null` = la séquence entière). `code`/`message` viennent de l'erreur typée du domaine.
export interface Anomalie {
  code: string
  message: string
  ordre: number | null
  gravite: Gravite
}

// Une flèche du schéma : le même objet est la *sortie* du bloc amont et l'*entrée* du bloc aval.
export interface Flux {
  ordre_source: number
  ordre_cible: number
  nature: NatureSource
  effectif: number | null
  rang_debut: number | null
  rang_fin: number | null
  tour: number | null
  issue: IssueTour | null
}

// Un tour d'un tableau et son **braquet** : les rangs que se partagent gagnants et perdants
// (Règle R de `moteur-placement-lucky-loser.md`). Plages **absolues** (rangs du tournoi).
export interface Tour {
  tour: number
  duels: number
  plage_gagnants: [number, number]
  plage_perdants: [number, number]
}

// Un bloc du schéma — les quatre questions du CA : qui est là, ce qu'on leur demande, où ils vont
// après, combien de tours.
export interface Bloc {
  ordre: number
  type: TypePhase
  effectif: number | null
  tranche: [number, number] | null
  nb_volees: number | null
  nb_fleches_par_volee: number | null
  tours: Tour[]
  entrees: Flux[]
  sorties: Flux[]
  // Combien d'archers voient leur tournoi s'arrêter dans ce bloc. Ce n'est **pas** une anomalie :
  // les non-qualifiés gardent leur rang. Le CA demande que le dessin le montre, pas qu'il s'en
  // alarme. ⚠️ **Signé** : un négatif signifie que les phases avales prélèvent, ensemble, plus de
  // participants que ce bloc n'en compte — une sur-souscription, signalée par ailleurs en anomalie.
  sans_suite: number | null
  // ⚠️ **Facultatif** : le suivi d'une édition (E07US004) ne rend pas d'anomalies — un tournoi en
  // cours n'est plus un brouillon qu'on diagnostique. Absent vaut « rien à signaler ».
  anomalies?: Anomalie[]
}

// --- Le calque de réalité (E07US004) -------------------------------------------------------------

// Statut d'une phase dans son cycle de vie (E12US008). Miroir de `domain.phase.StatutPhase`.
export type StatutPhase = 'a_venir' | 'en_cours' | 'en_pause' | 'terminee'

// Le remplissage d'un braquet : combien de duels y sont **tranchés** sur ceux **attendus**.
export interface AvancementTour {
  tour: number
  duels_attendus: number
  duels_joues: number
}

// Ce qui se superpose à un bloc quand on regarde une édition **en cours** plutôt qu'un format.
// Apparié au bloc par `ordre` — jamais fusionné avec lui, pour que le dessin reste identique aux
// trois surfaces et que seule la superposition change.
export interface AvancementBloc {
  ordre: number
  statut: StatutPhase
  tour_courant: number | null
  /** Combien de tours cette phase compte — **pas** `tours.length` (E05US032, ADR-0090).
   *
   * `tours` porte les *braquets*, les tranches de rangs qu'un tableau attribue au fil de l'eau, et
   * une phase qui ne classe qu'à la fin n'en a aucun tout en avançant par tours : un système suisse
   * en compte cinq. C'est la confusion qui faisait afficher « zéro tour » hors tableau. */
  nb_tours: number
  /** Le nom que la salle donne au tour en cours — « Demi-finale », « Ronde 3 », « Manche 2 ».
   *
   * **Servi par le backend, jamais recalculé ici** : la règle « à rebours de la finale » a déjà deux
   * domiciles (`DETTE-020`, dont `saisie-duels/duel.ts`), et en dériver un troisième est ce que le
   * CA d'E05US032 interdit nommément. `null` quand la phase n'annonce pas de tour — une
   * qualification est *une* étape, elle ne se dit pas « tour 1 sur 1 ». */
  libelle_tour_courant: string | null
  duels_joues: number
  duels_attendus: number
  tours: AvancementTour[]
}

export const LIBELLE_STATUT: Record<StatutPhase, string> = {
  a_venir: 'à venir',
  en_cours: 'en cours',
  en_pause: 'en pause',
  terminee: 'terminée',
}
