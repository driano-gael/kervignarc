// Hooks React Query de la feature « scoreurs » (E10US003).
//
// La liste des scoreurs d'un tournoi est de l'état **serveur** (lecture admin) ; créer/renommer/
// supprimer sont des **mutations** qui invalident cette liste (rafraîchissement immédiat, en plus
// de la diffusion temps réel post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  creerScoreur,
  getQrScoreur,
  getScoreurs,
  modifierScoreur,
  type NouveauScoreur,
  supprimerScoreur,
  telechargerCartesScoreurs,
} from './api'

const cleScoreurs = (tournoiId: number) => ['scoreurs', tournoiId] as const

export function useScoreurs(tournoiId: number) {
  return useQuery({
    queryKey: cleScoreurs(tournoiId),
    queryFn: () => getScoreurs(tournoiId),
  })
}

export function useCreerScoreur(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouveauScoreur) => creerScoreur(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleScoreurs(tournoiId) }),
  })
}

export function useModifierScoreur(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ scoreurId, entree }: { scoreurId: number; entree: NouveauScoreur }) =>
      modifierScoreur(tournoiId, scoreurId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleScoreurs(tournoiId) }),
  })
}

export function useSupprimerScoreur(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (scoreurId: number) => supprimerScoreur(tournoiId, scoreurId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleScoreurs(tournoiId) }),
  })
}

// Le PDF des cartes de scoreur (A08, 04/08/2026) : une **action** ponctuelle, comme le PDF des
// etiquettes de cible — `useMutation`, jamais `useQuery`.
export function useTelechargerCartesScoreurs(tournoiId: number) {
  return useMutation({ mutationFn: () => telechargerCartesScoreurs(tournoiId) })
}

// QR de session d'un scoreur (E16US015). ⚠️ **`enabled` n'est pas une optimisation ici, c'est la
// mesure de sécurité de l'US** : le QR ne se charge que sur geste explicite de l'admin (arbitrage
// du 04/09/2026, un seul scoreur à la fois). Sans lui, ouvrir l'écran afficherait tous les codes
// sous forme scannable — photographiables d'un cliché. Le cache React Query (règle 10) évite un
// rechargement à chaque ouverture/fermeture du même QR.
export function useQrScoreur(tournoiId: number, scoreurId: number, actif: boolean) {
  return useQuery({
    queryKey: ['qr-scoreur', tournoiId, scoreurId] as const,
    queryFn: () => getQrScoreur(tournoiId, scoreurId),
    enabled: actif,
  })
}
