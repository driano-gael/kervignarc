// Accès API de la feature « séquence de phases » (E05US001) : composer/éditer/ordonner/supprimer
// les phases d'un tournoi et faire vivre leur cycle de vie. Miroir des DTO de `api/v1/phases.py`.

import { fetchJson } from '../../shared/api/client'
import type { IssueTour, NatureSource, TypePhase } from '../../shared/phases/catalogue'
import type { ReglagePoules } from '../../shared/phases/poules'
import type { ReglageBigShootOff } from '../../shared/phases/bigShootOff'
import type { ArretProgramme } from '../../shared/phases/arrets'
import type { Decoupage } from '../../shared/phases/decoupage'
import type { ReglageSuisse } from '../../shared/phases/suisse'
import type { ReglageColline } from '../../shared/phases/colline'
import type { Profondeur } from '../patrimoine/api'

// Types de phase, natures de prélèvement et issues de tour : **ré-exportés** du catalogue partagé
// (`shared/phases/catalogue.ts`). Ils y ont été extraits en E01US024, à la 3ᵉ occurrence — le seuil
// que DETTE-030 se fixait elle-même. Les imports existants (`import type { TypePhase } from
// './api'`) continuent de marcher : il n'y a plus qu'un domicile à synchroniser avec le backend.
export type { IssueTour, NatureSource, TypePhase } from '../../shared/phases/catalogue'

// Cycle de vie d'une phase (ADR-0045 §1) : `en_pause` gèle la phase, distinct du tournoi.
export type StatutPhase = 'a_venir' | 'en_cours' | 'en_pause' | 'terminee'

// Transitions du cycle de vie, miroir de l'enum `TransitionPhase` du backend.
export type TransitionPhase = 'demarrer' | 'mettre_en_pause' | 'reprendre' | 'terminer'

// Un prélèvement de participants dans une phase antérieure. Une phase en porte **plusieurs**
// (E05US010). Selon `nature` : les rangs [rang_debut..rang_fin] (`rang_fin: null` = « et
// suivants »), les gagnants/perdants d'un `tour`, ou « le reste » de ce qu'aucune autre n'a pris.
export interface SourcePhase {
  ordre_source: number
  nature: NatureSource
  rang_debut: number
  rang_fin: number | null
  tour: number | null
  issue: IssueTour | null
}

// ⚠️ **Une étape définit, une phase avance** (E01US025, ADR-0076). Le déroulé se compose **une
// fois** au tournoi ; chaque créneau le rejoue en portant son propre avancement. Les deux formes se
// ressemblent parce que l'une décrit ce que l'autre joue — les confondre reviendrait à rétablir les
// N copies libres de diverger que l'ADR vient de supprimer.
//
// L'**étape** : la définition, portée par le tournoi. Aucun statut, aucun créneau.
export interface EtapeDeroule {
  id: number
  tournoi_id: number
  ordre: number
  type: TypePhase
  // [] = première de la séquence (alimentée par les inscriptions).
  sources: SourcePhase[]
  // null = effectif non déclaré (borne les rangs prélevables et le contrôle « effectif incompatible »).
  effectif: number | null
  // Rang jusqu'auquel les ex æquo se départagent **au tir** (E06US003, ADR-0066). `null` = aucun
  // barrage, donc l'ex æquo partagé qui est le défaut du produit.
  barrage_jusqu_au: number | null
  // Jusqu'où cette phase départage (E06US006, ADR-0070). `null` = **non réglée**, donc le preset de
  // son type — le podium pour un tableau. Pas « 1→N » : l'absence rejoue ce qui se jouait hier.
  profondeur: Profondeur | null
  // Le réglage d'une phase de **poules** (E05US023, ADR-0083). `null` = non réglée, ce qui est
  // licite : le type se choisit avant ses paramètres. C'est la composition du jour J qui l'exigera.
  poules: ReglagePoules | null
  // Le réglage d'un **Big Shoot Off** (E05US028) — combien sortent, manche par manche.
  // `null` = non réglé, ce qui est licite : le type se choisit avant ses paramètres.
  big_shoot_off: ReglageBigShootOff | null
  // Le réglage d'un **système suisse** (E05US030) — le nombre de rondes. Même régime que les deux
  // ci-dessus : `null` = non réglé, et le `PUT` étant une édition totale, l'omettre l'**efface**.
  suisse: ReglageSuisse | null
  // Le réglage d'une **colline** (E05US027) — nombre de manches et portée de défi. Même régime que
  // les trois ci-dessus. ⚠️ **Deux champs pour un seul réglage** : la portée distingue le King of
  // the Hill (1) du Ladder (2+), deux formats du référentiel §10.1 que la règle 2 range en un seul.
  colline: ReglageColline | null
  // Le **découpage d'une qualification en tours** (E05US035, ADR-0093) — « 20 volées en 2 tours de
  // 10 ». `null` = non découpée, l'état de toute qualification existante. Même régime d'édition
  // totale que ses voisins.
  decoupage: Decoupage | null

  // Le nombre de volées du barème de l'étape — **lecture seule** (E05US035). Sert à la fiche de
  // découpage, qui annonce ce que le réglage donne (« 2 tours de 10 volées ») et nomme le refus à
  // venir quand il ne tombe pas juste. `null` hors qualification. Le barème lui-même se règle par
  // sa propre ressource : ce champ ne part jamais au `PUT`.
  nb_volees: number | null
  // Les **pauses programmées** de cette étape (E05US033, ADR-0091) — `[]` = aucune, et c'est le
  // défaut : la salle enchaîne les tours toute seule.
  //
  // ⚠️ **Porté par l'étape, donc par le tournoi** (ADR-0076) : tous les créneaux rejouent les mêmes
  // pauses. `Phase` hérite du champ par le `Omit` ci-dessous, mais le serveur ne le remplit **que**
  // sur `EtapeReponse` — un `Phase` le rend toujours vide, puisque l'agrégat `Phase` ne le porte pas.
  // Ne pas s'en servir depuis une phase : l'écran d'atelier lit l'étape.
  arrets: ArretProgramme[]

  // Le **libellé** que l'organisateur donne à cette étape (E16US002) — `null` = aucun, l'écran
  // retombe alors sur le libellé du type. C'est ce qui rend deux qualifications distinguables à
  // l'œil une fois qu'E05US024/E05US025 les ont rendues composables.
  //
  // Servi **normalisé** par le serveur (espaces de bord retirés, blanc ramené à `null`) : le client
  // n'a rien à nettoyer. ⚠️ Comme ses voisins, l'édition est **totale** — omis au `PUT`, il est
  // effacé, et c'est le seul geste par lequel on retire un titre.
  titre: string | null
}

// La **phase** : l'avancement d'une étape dans un créneau — la définition **assemblée** par le
// serveur, plus `depart_id`, `statut` et son propre `id`, celui auquel s'adressent les transitions.
//
// ⚠️ **`arrets`, `nb_volees` et `titre` sont retirés du type, pas seulement commentés** — trois
// fois le même défaut (E05US034, E05US035, E16US002). Le serveur ne sert ces champs que sur
// `EtapeReponse` : sur une `Phase` ils valent `undefined` à l'exécution pendant que TS garantissait
// une valeur. C'est le `Omit` explicite qui rend la couture visible.
export interface Phase extends Omit<EtapeDeroule, 'tournoi_id' | 'arrets' | 'nb_volees' | 'titre'> {
  depart_id: number
  statut: StatutPhase
}

// Config de séquence envoyée au serveur (ajout et édition totale partagent la même forme).
//
// ⚠️ **Édition totale** : un champ omis est **effacé** côté serveur. C'est pourquoi
// `barrage_jusqu_au` doit être renvoyé à chaque `PUT`, réhydraté depuis la phase — sans quoi
// corriger l'effectif d'une phase effacerait son seuil de barrage en silence. `profondeur` (E06US006)
// tombe sous la même règle, avec une conséquence plus lourde encore : effacée, la phase retombe sur
// son preset, et un tournoi composé en placement intégral se rejouerait tronqué au podium.
export interface ConfigPhase {
  type: TypePhase
  sources?: SourcePhase[]
  effectif?: number | null
  barrage_jusqu_au?: number | null
  profondeur?: Profondeur | null
  // Même règle d'édition totale : omis, le réglage de poules est **effacé** côté serveur.
  poules?: ReglagePoules | null
  // Même règle d'édition totale : omis, le réglage du Big Shoot Off est **effacé** côté serveur.
  big_shoot_off?: ReglageBigShootOff | null
  // Même règle d'édition totale : omis, le réglage du système suisse est **effacé** côté serveur.
  suisse?: ReglageSuisse | null
  // Même règle d'édition totale : omis, le réglage de la colline est **effacé** côté serveur.
  colline?: ReglageColline | null
  // Même règle d'édition totale : omis, le découpage de la qualification est **effacé** côté
  // serveur. C'est ce qui permet de retyper une qualification découpée sans se faire refuser
  // l'édition — le serveur lève sinon `DecoupageEnToursInvalide` sur un réglage devenu fantôme.
  decoupage?: Decoupage | null
  // ⚠️ **Même règle, et c'est ici qu'elle coûte le plus cher** : une liste omise ou vide **supprime**
  // toutes les pauses programmées. Ce n'est pas un paramètre qu'on retrouve d'un coup d'œil mais un
  // planning de journée saisi ligne à ligne. L'écran renvoie donc toujours la liste complète.
  arrets?: ArretProgramme[]
  // Même règle d'édition totale : omis, le titre est **effacé** côté serveur (E16US002). Voir
  // `configInchangee` dans `Phases.tsx` — les widgets qui n'éditent qu'un champ doivent réémettre
  // celui-ci, faute de quoi régler un barrage renomme la phase en silence.
  titre?: string | null
}

// --- Composition : le déroulé du tournoi (atelier) ----------------------------------------------

export function getPhases(tournoiId: number): Promise<EtapeDeroule[]> {
  return fetchJson<EtapeDeroule[]>(`/api/v1/tournois/${tournoiId}/phases`)
}

export function ajouterPhase(tournoiId: number, config: ConfigPhase): Promise<EtapeDeroule> {
  return fetchJson<EtapeDeroule>(`/api/v1/tournois/${tournoiId}/phases`, {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

export function modifierPhase(
  tournoiId: number,
  etapeId: number,
  config: ConfigPhase,
): Promise<EtapeDeroule> {
  return fetchJson<EtapeDeroule>(`/api/v1/tournois/${tournoiId}/phases/${etapeId}`, {
    method: 'PUT',
    body: JSON.stringify(config),
  })
}

export function reordonnerPhases(tournoiId: number, phases: number[]): Promise<EtapeDeroule[]> {
  return fetchJson<EtapeDeroule[]>(`/api/v1/tournois/${tournoiId}/phases/reordonner`, {
    method: 'POST',
    body: JSON.stringify({ phases }),
  })
}

export function supprimerPhase(tournoiId: number, etapeId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/phases/${etapeId}`, { method: 'DELETE' })
}

// --- Avancement : ce qu'un créneau a joué (pilotage) --------------------------------------------

// Les phases d'un créneau, ordonnées, définition assemblée et statut à jour. C'est **ici** que
// vivent les identifiants auxquels s'adressent les transitions : le déroulé du tournoi n'en a pas.
export function getAvancement(departId: number): Promise<Phase[]> {
  return fetchJson<Phase[]>(`/api/v1/departs/${departId}/phases`)
}

export function changerStatutPhase(
  departId: number,
  phaseId: number,
  transition: TransitionPhase,
): Promise<Phase> {
  return fetchJson<Phase>(`/api/v1/departs/${departId}/phases/${phaseId}/statut`, {
    method: 'POST',
    body: JSON.stringify({ transition }),
  })
}
