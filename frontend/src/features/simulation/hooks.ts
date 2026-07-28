// Hooks React Query du cockpit de simulation (E15US003).
//
// L'état d'une session est **serveur** (en mémoire) : `useEtatSimulation` le lit, les mutations le
// font avancer/pauser/etc. Chaque action renvoie l'état frais — on **écrit le cache** avec (pas de
// refetch superflu). Le canal `/ws/simulation` (isolé, ADR-0055 §5) invalide ce cache si un autre
// client agit ; branché dans le composant (`Simulation`).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from './api'
import type { Cote, DetailArcher, EtatSession } from './api'

export const cleSession = (sessionId: number) => ['simulation', sessionId] as const

export function useEtatSimulation(sessionId: number | null) {
  return useQuery({
    queryKey: sessionId === null ? ['simulation', 'aucune'] : cleSession(sessionId),
    queryFn: () => api.etatSession(sessionId as number),
    enabled: sessionId !== null,
  })
}

export function useDetailArcher(sessionId: number | null, archerId: number | null) {
  return useQuery({
    queryKey: ['simulation', sessionId, 'archer', archerId],
    queryFn: () => api.detailArcher(sessionId as number, archerId as number),
    enabled: sessionId !== null && archerId !== null,
  })
}

export function useDemarrerSimulation() {
  return useMutation<EtatSession, Error, { tournoiId: number; graine?: number }>({
    mutationFn: ({ tournoiId, graine }) => api.demarrer(tournoiId, graine),
  })
}

// Fabrique une mutation d'action sur une session : elle écrit l'état renvoyé dans le cache (et
// invalide le détail archer, dont les volées ont pu changer). Évite de répéter le `onSuccess`.
function useActionSimulation<V>(action: (valeur: V) => Promise<EtatSession>) {
  const queryClient = useQueryClient()
  return useMutation<EtatSession, Error, V>({
    mutationFn: action,
    onSuccess: (etat) => {
      queryClient.setQueryData(cleSession(etat.session_id), etat)
      void queryClient.invalidateQueries({ queryKey: ['simulation', etat.session_id, 'archer'] })
    },
  })
}

export function useAvancer() {
  return useActionSimulation<{ sessionId: number; nbPas?: number }>(({ sessionId, nbPas }) =>
    api.avancer(sessionId, nbPas),
  )
}

export function useTerminer() {
  return useActionSimulation<number>((sessionId) => api.terminer(sessionId))
}

export function usePause() {
  return useActionSimulation<number>((sessionId) => api.pause(sessionId))
}

export function useReprendre() {
  return useActionSimulation<number>((sessionId) => api.reprendre(sessionId))
}

export function useSaisirVolee() {
  return useActionSimulation<{
    sessionId: number
    archerId: number
    numeroVolee: number
    valeurs: string[]
  }>(({ sessionId, archerId, numeroVolee, valeurs }) =>
    api.saisirVolee(sessionId, archerId, numeroVolee, valeurs),
  )
}

export function useDesignerVainqueur() {
  return useActionSimulation<{
    sessionId: number
    phaseId: number
    matchNumero: number
    cote: Cote
  }>(({ sessionId, phaseId, matchNumero, cote }) =>
    api.designerVainqueur(sessionId, phaseId, matchNumero, cote),
  )
}

export type { DetailArcher, EtatSession }
