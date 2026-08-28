// Cas d'usage React Query des forfaits (E04US015, ADR-0050).
//
// Chaque mutation invalide la vue concernée : un forfait de **qualification** rejoue le classement
// (relégation / exclusion, `['classement', tournoiId]`) ; un forfait de **duels** rejoue le tableau
// (`['duels-tableau', tournoiId, phaseId]`, où le walkover apparaît). Les clés sont reprises
// telles quelles des features `competition` / `saisie-duels` — invalider suffit à resynchroniser.

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { cleClassement } from '../competition/hooks'
import {
  annulerForfaitDuel,
  annulerForfaitQualif,
  declarerForfaitDuel,
  declarerForfaitQualif,
  type NatureForfait,
} from './api'

const cleTableau = (tournoiId: number, phaseId: number) =>
  ['duels-tableau', tournoiId, phaseId] as const

export function useDeclarerForfaitQualif(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      archerId,
      nature,
      motif,
    }: {
      archerId: number
      nature: NatureForfait
      motif?: string
    }) => declarerForfaitQualif(tournoiId, archerId, nature, motif),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}

export function useAnnulerForfaitQualif(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (archerId: number) => annulerForfaitQualif(tournoiId, archerId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}

export function useDeclarerForfaitDuel(tournoiId: number, phaseId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      archerId,
      nature,
      motif,
    }: {
      archerId: number
      nature: NatureForfait
      motif?: string
    }) => declarerForfaitDuel(tournoiId, phaseId, archerId, nature, motif),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleTableau(tournoiId, phaseId) }),
  })
}

// ⚠️ DETTE-090 : hook **sans appelant** — la surface d'annulation d'un forfait de duel n'existe
// pas encore. Ce n'est pas du code mort à supprimer : c'est la moitié livrée de `D-15`.
export function useAnnulerForfaitDuel(tournoiId: number, phaseId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (archerId: number) => annulerForfaitDuel(tournoiId, phaseId, archerId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleTableau(tournoiId, phaseId) }),
  })
}
