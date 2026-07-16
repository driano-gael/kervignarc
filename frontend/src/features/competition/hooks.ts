// Hooks React Query de la feature « competition » (E00US011).
//
// Le classement est l'état **serveur** (lecture) ; les autres cas d'usage sont des
// **mutations**. Après chaque écriture, le backend diffuse un événement WebSocket qui, via
// `useRealtime`, invalide le cache — le classement se met donc à jour **en direct** sur tous
// les clients. On invalide aussi côté mutation (onSuccess) pour un rafraîchissement immédiat
// même si le lien temps réel est momentanément coupé.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ajouterArcher,
  creerTournoi,
  demarrerTournoi,
  getClassement,
  getTournois,
  type ModifierTournoi,
  modifierTournoi,
  type NouvelArcher,
  placerArcher,
  saisirScore,
  supprimerTournoi,
  terminerTournoi,
} from './api'

// Exportée : la feature `archers` (E02US003) invalide le classement après une édition ou une
// désinscription — un archer corrigé ou retiré doit quitter le tableau sans attendre. La clé se
// déclare **une fois**, ici, où vit la requête ; deux littéraux `['classement', id]` finiraient
// par diverger et l'invalidation raterait sa cible en silence.
export const cleClassement = (tournoiId: number) => ['classement', tournoiId] as const
const CLE_TOURNOIS = ['tournois'] as const

export function useClassement(tournoiId: number) {
  return useQuery({
    queryKey: cleClassement(tournoiId),
    queryFn: () => getClassement(tournoiId),
  })
}

export function useTournois() {
  return useQuery({ queryKey: CLE_TOURNOIS, queryFn: getTournois })
}

export function useCreerTournoi() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: creerTournoi,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS }),
  })
}

// Édition et cycle de vie (E01US002). Chaque mutation invalide la liste des tournois : la
// vue se resynchronise (statut, métadonnées, disparition d'un tournoi supprimé).
export function useModifierTournoi() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, entree }: { id: number; entree: ModifierTournoi }) =>
      modifierTournoi(id, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS }),
  })
}

export function useDemarrerTournoi() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => demarrerTournoi(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS }),
  })
}

export function useTerminerTournoi() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => terminerTournoi(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS }),
  })
}

export function useSupprimerTournoi() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => supprimerTournoi(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS }),
  })
}

export function useAjouterArcher(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouvelArcher) => ajouterArcher(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}

export function usePlacerArcher(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ archerId, cible }: { archerId: number; cible: number }) =>
      placerArcher(archerId, cible),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}

export function useSaisirScore(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ archerId, points }: { archerId: number; points: number }) =>
      saisirScore(archerId, points),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}
