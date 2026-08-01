// Accès API de la feature « séquence de phases » (E05US001) : composer/éditer/ordonner/supprimer
// les phases d'un tournoi et faire vivre leur cycle de vie. Miroir des DTO de `api/v1/phases.py`.

import { fetchJson } from '../../shared/api/client'

// Types de phase déclarables (ADR-0045 §2) — le catalogue est peuplé par E05US015 (ADR-0062).
// ⚠️ Cette union est **dupliquée** dans `features/patrimoine/api.ts` (les formats de bibliothèque
// composent les mêmes types). Deux copies, donc deux occasions de diverger du backend : c'est
// assumé tant qu'il n'y en a que deux — à une 3ᵉ, l'extraire dans un module partagé se justifiera.
// DETTE-030 (../../../../docs/dette.md) : cette union est déclarée **deux fois** côté front (ici et
// dans l'autre feature), et doit rester synchronisée avec l'enum `TypePhase` du backend — trois
// domiciles pour une vérité. Assumé à deux occurrences ; ce qui rend la duplication tenable est que
// **chaque consommateur soit exhaustif** (`Record` ou `switch` + `assertNever`), jamais un ternaire
// à repli — le repli est précisément ce qui a fait afficher six types comme « Placement ».
export type TypePhase =
  | 'qualification'
  | 'elimination_directe'
  | 'placement'
  | 'echauffement'
  | 'barrage'
  | 'poules'
  | 'big_shoot_off'
  | 'suisse'
  | 'colline'

// Cycle de vie d'une phase (ADR-0045 §1) : `en_pause` gèle la phase, distinct du tournoi.
export type StatutPhase = 'a_venir' | 'en_cours' | 'en_pause' | 'terminee'

// Transitions du cycle de vie, miroir de l'enum `TransitionPhase` du backend.
export type TransitionPhase = 'demarrer' | 'mettre_en_pause' | 'reprendre' | 'terminer'

// Comment un prélèvement puise dans la phase amont (E05US010, miroir de `NatureSource`).
export type NatureSource = 'rangs' | 'issue_de_tour' | 'reste'

// Le côté d'un tour dont on prélève (miroir de `IssueTour`).
export type IssueTour = 'gagnants' | 'perdants'

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
}

// Config de séquence envoyée au serveur (ajout et édition totale partagent la même forme).
export interface ConfigPhase {
  type: TypePhase
  sources?: SourcePhase[]
  effectif?: number | null
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
