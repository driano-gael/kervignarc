// Hooks React Query de la feature « paiements » (E08US002).
//
// Les vues (par archer, par club) sont de l'état **serveur** (lecture) ; marquer un archer / un club
// sont des **mutations** qui invalident **les deux** vues du tournoi (un règlement change autant le
// détail par archer que les totaux par club), en plus de la diffusion temps réel post-commit.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cleCompletude } from '../completude/hooks'
import {
  getPaiementsArchers,
  getPaiementsClubs,
  getRemboursements,
  type IssueRemboursement,
  marquerArcher,
  marquerClub,
  traiterRemboursement,
} from './api'

const cleArchers = (tournoiId: number) => ['paiements', 'archers', tournoiId] as const
const cleClubs = (tournoiId: number) => ['paiements', 'clubs', tournoiId] as const
// Clé alignée sur celle qu'invalide la désinscription (feature « inscriptions ») : les deux vues
// se rafraîchissent quand un poste s'ouvre.
const cleRemboursements = (tournoiId: number) => ['remboursements', tournoiId] as const

export function usePaiementsArchers(tournoiId: number) {
  return useQuery({
    queryKey: cleArchers(tournoiId),
    queryFn: () => getPaiementsArchers(tournoiId),
  })
}

export function usePaiementsClubs(tournoiId: number) {
  return useQuery({
    queryKey: cleClubs(tournoiId),
    queryFn: () => getPaiementsClubs(tournoiId),
  })
}

// Invalide les deux vues du tournoi : marquer un paiement modifie le détail par archer **et** les
// totaux par club — les deux caches doivent se rafraîchir.
//
// E16US003 — **plus la complétude**. Depuis que l'encart administratif est rendu en tête de cet
// écran, le compteur « 113/120 » et le tableau qui le suit lisent la même réalité : sans cette
// invalidation, le tableau basculait sur « Réglé » instantanément pendant que l'encart gardait
// l'ancien compte jusqu'au prochain tick du poll (5 s). Le même écran se contredisait — exactement
// ce que le CA « deux écrans, une source » veut rendre impossible.
function useInvaliderPaiements(tournoiId: number) {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: cleArchers(tournoiId) })
    void queryClient.invalidateQueries({ queryKey: cleClubs(tournoiId) })
    void queryClient.invalidateQueries({ queryKey: cleCompletude(tournoiId) })
  }
}

export function useMarquerArcher(tournoiId: number) {
  const invalider = useInvaliderPaiements(tournoiId)
  return useMutation({
    mutationFn: ({ archerId, paye }: { archerId: number; paye: boolean }) =>
      marquerArcher(tournoiId, archerId, paye),
    onSuccess: invalider,
  })
}

export function useMarquerClub(tournoiId: number) {
  const invalider = useInvaliderPaiements(tournoiId)
  return useMutation({
    mutationFn: ({ clubId, paye }: { clubId: number; paye: boolean }) =>
      marquerClub(tournoiId, clubId, paye),
    onSuccess: invalider,
  })
}

export function useRemboursements(tournoiId: number) {
  return useQuery({
    queryKey: cleRemboursements(tournoiId),
    queryFn: () => getRemboursements(tournoiId),
  })
}

export function useTraiterRemboursement(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      remboursementId,
      statut,
    }: {
      remboursementId: number
      statut: IssueRemboursement
    }) => traiterRemboursement(tournoiId, remboursementId, statut),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleRemboursements(tournoiId) }),
  })
}
