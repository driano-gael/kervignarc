// Hooks React Query de la feature « paiements » (E08US002).
//
// Les vues (par archer, par club) sont de l'état **serveur** (lecture) ; marquer un archer / un club
// sont des **mutations** qui invalident **les deux** vues du tournoi (un règlement change autant le
// détail par archer que les totaux par club), en plus de la diffusion temps réel post-commit.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getPaiementsArchers, getPaiementsClubs, marquerArcher, marquerClub } from './api'

const cleArchers = (tournoiId: number) => ['paiements', 'archers', tournoiId] as const
const cleClubs = (tournoiId: number) => ['paiements', 'clubs', tournoiId] as const

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
function useInvaliderPaiements(tournoiId: number) {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: cleArchers(tournoiId) })
    void queryClient.invalidateQueries({ queryKey: cleClubs(tournoiId) })
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
