// Cas d'usage React Query des forfaits (E04US015, ADR-0050).
//
// Chaque mutation invalide la vue concernée : un forfait de **qualification** rejoue le classement
// (relégation / exclusion, `['classement', tournoiId]`) ; un forfait de **duels** rejoue le tableau
// (`cleTableau`, où le walkover apparaît). Les clés sont **importées** de leur feature
// propriétaire — `competition` et `saisie-duels` —, jamais recopiées : une clé qui diverge
// n'invalide plus rien et rien ne rougit (le symptôme est une vue périmée, pas une erreur).

import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { PorteeAuth } from '../../shared/api/client'
import { cleClassement } from '../competition/hooks'
import { cleTableau } from '../saisie-duels/hooks'
import {
  annulerForfaitDuel,
  annulerForfaitQualif,
  declarerForfaitDuel,
  declarerForfaitQualif,
  type NatureForfait,
} from './api'

// `portee` par défaut `'scoreur'` : l'espace scoreur, seul appelant jusqu'à E16US007, ne change
// pas d'identité. La fiche d'archer du pilotage passe `'admin'`.
export function useDeclarerForfaitQualif(tournoiId: number, portee: PorteeAuth = 'scoreur') {
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
    }) => declarerForfaitQualif(tournoiId, archerId, nature, motif, portee),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}

export function useAnnulerForfaitQualif(tournoiId: number, portee: PorteeAuth = 'scoreur') {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (archerId: number) => annulerForfaitQualif(tournoiId, archerId, portee),
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
