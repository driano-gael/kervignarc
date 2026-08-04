// Accès API de la feature « séquence de phases » (E05US001) : composer/éditer/ordonner/supprimer
// les phases d'un tournoi et faire vivre leur cycle de vie. Miroir des DTO de `api/v1/phases.py`.

import { fetchJson } from '../../shared/api/client'
import type { IssueTour, NatureSource, TypePhase } from '../../shared/phases/catalogue'
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

export interface Phase {
  id: number
  tournoi_id: number
  ordre: number
  type: TypePhase
  statut: StatutPhase
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
}

export function getPhases(tournoiId: number): Promise<Phase[]> {
  return fetchJson<Phase[]>(`/api/v1/tournois/${tournoiId}/phases`)
}

export function ajouterPhase(tournoiId: number, config: ConfigPhase): Promise<Phase> {
  return fetchJson<Phase>(`/api/v1/tournois/${tournoiId}/phases`, {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

export function modifierPhase(
  tournoiId: number,
  phaseId: number,
  config: ConfigPhase,
): Promise<Phase> {
  return fetchJson<Phase>(`/api/v1/tournois/${tournoiId}/phases/${phaseId}`, {
    method: 'PUT',
    body: JSON.stringify(config),
  })
}

export function reordonnerPhases(tournoiId: number, phases: number[]): Promise<Phase[]> {
  return fetchJson<Phase[]>(`/api/v1/tournois/${tournoiId}/phases/reordonner`, {
    method: 'POST',
    body: JSON.stringify({ phases }),
  })
}

export function supprimerPhase(tournoiId: number, phaseId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/phases/${phaseId}`, { method: 'DELETE' })
}

export function changerStatutPhase(
  tournoiId: number,
  phaseId: number,
  transition: TransitionPhase,
): Promise<Phase> {
  return fetchJson<Phase>(`/api/v1/tournois/${tournoiId}/phases/${phaseId}/statut`, {
    method: 'POST',
    body: JSON.stringify({ transition }),
  })
}
