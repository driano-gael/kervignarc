// Hooks React Query de la feature « clubs » (E02US001).
//
// Le référentiel est de l'état **serveur** (lecture) ; créer/renommer/supprimer sont des
// **mutations** qui invalident la liste (rafraîchissement immédiat, en plus de la diffusion
// temps réel post-commit côté serveur).
//
// La clé de cache n'est **pas** paramétrée par un tournoi (contrairement à `blasons` ou
// `categories`) : le référentiel est global.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  creerClub,
  getClubs,
  type ModifierClub,
  modifierClub,
  type NouveauClub,
  supprimerClub,
} from './api'

const cleClubs = ['clubs'] as const

export function useClubs() {
  return useQuery({
    queryKey: cleClubs,
    queryFn: getClubs,
  })
}

export function useCreerClub() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouveauClub) => creerClub(entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClubs }),
  })
}

export function useModifierClub() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, entree }: { id: number; entree: ModifierClub }) => modifierClub(id, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClubs }),
  })
}

export function useSupprimerClub() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => supprimerClub(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClubs }),
  })
}
