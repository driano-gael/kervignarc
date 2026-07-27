// Hooks React Query de la feature « departs » (E02US004, ADR-0017).
//
// La liste des départs d'un tournoi est de l'état **serveur** (lecture) ; créer/éditer/supprimer
// sont des **mutations** qui invalident cette liste (rafraîchissement immédiat, en plus de la
// diffusion temps réel post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  creerDepart,
  getDeparts,
  type ModifierDepart,
  modifierDepart,
  type NouveauDepart,
  supprimerDepart,
} from './api'

const cleDeparts = (tournoiId: number) => ['departs', tournoiId] as const

// `enabled` (défaut `true`) : la recherche de la sidebar admin (E12US006), montée sur tout écran, ne
// charge les départs que lorsqu'on cherche — les écrans existants ne passent rien et gardent leur
// comportement.
export function useDeparts(tournoiId: number, enabled = true) {
  return useQuery({
    queryKey: cleDeparts(tournoiId),
    queryFn: () => getDeparts(tournoiId),
    enabled,
  })
}

export function useCreerDepart(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouveauDepart) => creerDepart(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleDeparts(tournoiId) }),
  })
}

export function useModifierDepart(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    // `confirmeCycle` : rejoue l'édition d'un créneau lancé/clos après le signalement
    // `depart_en_cours_non_confirme` (E12US008).
    mutationFn: ({
      departId,
      entree,
      confirmeCycle,
    }: {
      departId: number
      entree: ModifierDepart
      confirmeCycle?: boolean
    }) => modifierDepart(tournoiId, departId, entree, confirmeCycle),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleDeparts(tournoiId) }),
  })
}

export function useSupprimerDepart(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    // `confirmeCycle` (créneau lancé/clos, E12US008) et `autoriserSuppressionInscrits` (créneau
    // ouvert à inscriptions, ADR-0018) lèvent chacun leur signalement respectif.
    mutationFn: ({
      departId,
      autoriserSuppressionInscrits,
      confirmeCycle,
    }: {
      departId: number
      autoriserSuppressionInscrits?: boolean
      confirmeCycle?: boolean
    }) => supprimerDepart(tournoiId, departId, autoriserSuppressionInscrits, confirmeCycle),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleDeparts(tournoiId) }),
  })
}
