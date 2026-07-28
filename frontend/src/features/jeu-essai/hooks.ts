// Hooks React Query de la feature « jeu d'essai » (E15US001).
//
// `useScenarios` : le catalogue (état **serveur**, lecture). `usePeuplerTournoi` / `useInstancierScenario`
// sont des **mutations** qui créent de la donnée réelle. Elles invalident les listes concernées
// (tournois, archers) pour un rafraîchissement immédiat — en plus de la diffusion temps réel
// post-commit, qui invalide déjà tout le cache (robustesse si la WS est déconnectée).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CLE_TOURNOIS } from '../competition/hooks'
import {
  getScenarios,
  instancierScenario,
  peuplerTournoi,
  type BilanPeuplement,
  type ResultatScenario,
  type Scenario,
} from './api'

const CLE_SCENARIOS = ['jeu-essai', 'scenarios'] as const
const cleArchers = (tournoiId: number) => ['archers', tournoiId] as const

export function useScenarios() {
  return useQuery({ queryKey: CLE_SCENARIOS, queryFn: getScenarios })
}

export function usePeuplerTournoi(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation<BilanPeuplement, Error, { nombre: number; graine?: number }>({
    mutationFn: ({ nombre, graine }) => peuplerTournoi(tournoiId, nombre, graine),
    onSuccess: () => {
      // Les archers du tournoi changent ; sa fiche (compteurs) aussi.
      void queryClient.invalidateQueries({ queryKey: cleArchers(tournoiId) })
      void queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS })
    },
  })
}

export function useInstancierScenario() {
  const queryClient = useQueryClient()
  return useMutation<ResultatScenario, Error, { scenarioId: string; graine?: number }>({
    mutationFn: ({ scenarioId, graine }) => instancierScenario(scenarioId, graine),
    onSuccess: (resultat) => {
      // Un nouveau tournoi apparaît dans le sélecteur, avec ses archers.
      void queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS })
      void queryClient.invalidateQueries({ queryKey: cleArchers(resultat.tournoi_id) })
    },
  })
}

export type { Scenario }
