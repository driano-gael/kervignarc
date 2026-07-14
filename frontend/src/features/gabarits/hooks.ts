// Hooks React Query de la feature « gabarits de salle » (E01US007).
//
// La liste des gabarits est de l'état **serveur** (lecture) ; créer/éditer/supprimer sont des
// **mutations** qui invalident cette liste (rafraîchissement immédiat, en plus de la diffusion
// temps réel post-commit côté serveur). Ressource globale : clé de cache sans identifiant de
// tournoi.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  type AjustementGabarit,
  ajusterGabarit,
  appliquerGabarit,
  creerGabarit,
  getGabaritDuTournoi,
  getGabarits,
  type ModifierGabarit,
  modifierGabarit,
  type NouveauGabarit,
  supprimerGabarit,
} from './api'

const cleGabarits = ['gabarits'] as const
const cleGabaritTournoi = (tournoiId: number) => ['gabarit-tournoi', tournoiId] as const

export function useGabarits() {
  return useQuery({
    queryKey: cleGabarits,
    queryFn: getGabarits,
  })
}

export function useCreerGabarit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouveauGabarit) => creerGabarit(entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleGabarits }),
  })
}

export function useModifierGabarit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, entree }: { id: number; entree: ModifierGabarit }) =>
      modifierGabarit(id, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleGabarits }),
  })
}

export function useSupprimerGabarit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => supprimerGabarit(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleGabarits }),
  })
}

// --- Plan de salle d'un tournoi (E01US008) ---

export function useGabaritDuTournoi(tournoiId: number) {
  return useQuery({
    queryKey: cleGabaritTournoi(tournoiId),
    queryFn: () => getGabaritDuTournoi(tournoiId),
  })
}

export function useAppliquerGabarit(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (modeleId: number) => appliquerGabarit(tournoiId, modeleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleGabaritTournoi(tournoiId) }),
  })
}

export function useAjusterGabarit(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: AjustementGabarit) => ajusterGabarit(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleGabaritTournoi(tournoiId) }),
  })
}
