// Qui n'a pas de cible — le compteur « Non placés » des inscriptions (A09, E17US007). Pur et testé.

import type { PlanDeCibles } from './api'

// Les plans du tournoi, un par départ ; `'sans_gabarit'` quand la salle n'est pas encore définie
// (aucun plan ne peut exister : personne n'est placé) ; `null` quand une lecture a échoué.
export type PlansDuTournoi = readonly PlanDeCibles[] | 'sans_gabarit' | null

// Non placé = en réserve sur au moins un départ, **ou** posé sur aucune cible d'aucun plan. ⚠️ Le
// second cas n'est pas redondant : l'archer inscrit au tournoi mais à **aucun** départ n'est dans
// aucune réserve — c'est l'archer oublié, celui que ce compteur existe pour montrer.
export function archersNonPlaces(
  archerIds: readonly number[],
  plans: PlansDuTournoi,
): ReadonlySet<number> | null {
  if (plans === null) return null
  if (plans === 'sans_gabarit') return new Set(archerIds)
  const poses = new Set(
    plans.flatMap((p) => p.cibles.flatMap((c) => c.placements.map((pl) => pl.archer_id))),
  )
  const enReserve = new Set(plans.flatMap((p) => p.conflits.map((c) => c.archer_id)))
  return new Set(archerIds.filter((id) => enReserve.has(id) || !poses.has(id)))
}
