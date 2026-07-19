// Hooks React Query de la saisie (E04US002) — état serveur de la grille, des séries et du contexte.
//
// Lectures : la grille du poste (dépend du **départ courant** en session serveur — un 409 tant qu'il
// n'est pas fixé, cf. `Saisie.tsx`), la série de chaque archer, le barème et le grain de la phase, la
// liste des départs. Écritures : fixer le départ courant, saisir une volée. Chaque écriture invalide
// ce qu'elle change (changer de départ change les archers ; saisir change la série de l'archer).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fixerDepartCourant,
  getBareme,
  getDepartsDuPoste,
  getGrain,
  getGrille,
  getSerie,
  saisirVolee,
  type SaisirVolee,
  type Serie,
} from './api'

const cleGrille = () => ['saisie-grille'] as const
const cleSerie = (tournoiId: number, archerId: number) =>
  ['saisie-serie', tournoiId, archerId] as const
const cleBareme = (tournoiId: number) => ['saisie-bareme', tournoiId] as const
const cleGrain = (tournoiId: number) => ['saisie-grain', tournoiId] as const
const cleDeparts = (tournoiId: number) => ['saisie-departs', tournoiId] as const

export function useGrille() {
  // Pas de `retry` : un 409 « départ courant non défini » est un état **attendu** (pas un incident
  // réseau) que `Saisie.tsx` inspecte pour afficher le sélecteur de départ — inutile de réessayer.
  return useQuery({ queryKey: cleGrille(), queryFn: getGrille, retry: false })
}

export function useSerie(tournoiId: number, archerId: number) {
  return useQuery({
    queryKey: cleSerie(tournoiId, archerId),
    queryFn: () => getSerie(tournoiId, archerId),
  })
}

export function useBareme(tournoiId: number) {
  return useQuery({ queryKey: cleBareme(tournoiId), queryFn: () => getBareme(tournoiId) })
}

export function useGrain(tournoiId: number) {
  return useQuery({ queryKey: cleGrain(tournoiId), queryFn: () => getGrain(tournoiId) })
}

export function useDeparts(tournoiId: number) {
  return useQuery({ queryKey: cleDeparts(tournoiId), queryFn: () => getDepartsDuPoste(tournoiId) })
}

export function useFixerDepart() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (departId: number) => fixerDepartCourant(departId),
    // Changer de départ change les archers servis **et** leurs séries : on invalide la grille et
    // toutes les séries en cache (préfixe `saisie-serie`) pour repartir de zéro sur le bon départ.
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cleGrille() })
      void queryClient.invalidateQueries({ queryKey: ['saisie-serie'] })
    },
  })
}

export function useSaisirVolee(tournoiId: number, archerId: number) {
  const queryClient = useQueryClient()
  return useMutation<Serie, Error, SaisirVolee>({
    mutationFn: (corps) => saisirVolee(corps),
    // L'accusé de réception (la série renvoyée) rafraîchit directement le cache de l'archer, puis on
    // invalide pour réconcilier le « quand » relu hors de l'unité idempotente côté serveur.
    onSuccess: (serie) => {
      queryClient.setQueryData(cleSerie(tournoiId, archerId), serie)
      void queryClient.invalidateQueries({ queryKey: cleSerie(tournoiId, archerId) })
    },
  })
}
