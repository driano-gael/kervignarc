// Hooks React Query de la feature « archers » (E02US003).
//
// La liste des inscrits d'un tournoi est de l'état **serveur** (lecture) ; éditer et désinscrire
// sont des **mutations**. Chacune invalide deux caches : la liste elle-même, et le **classement**
// — un archer corrigé y change de nom, un archer désinscrit doit en disparaître. C'est en plus de
// la diffusion temps réel post-commit, qui invalide tout le cache ; l'invalidation locale est le
// filet quand le lien WebSocket est momentanément coupé.
//
// La dépendance va d'ici vers `competition` (on lui emprunte `cleClassement`) et jamais l'inverse :
// un import croisé entre deux modules de hooks serait un cycle.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cleClassement } from '../competition/hooks'
import { getArchers, type ModifierArcher, modifierArcher, supprimerArcher } from './api'

const cleArchers = (tournoiId: number) => ['archers', tournoiId] as const

export function useArchers(tournoiId: number) {
  return useQuery({
    queryKey: cleArchers(tournoiId),
    queryFn: () => getArchers(tournoiId),
  })
}

function useInvaliderArchers(tournoiId: number) {
  const queryClient = useQueryClient()
  return async () => {
    await queryClient.invalidateQueries({ queryKey: cleArchers(tournoiId) })
    await queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
  }
}

export function useModifierArcher(tournoiId: number) {
  const invalider = useInvaliderArchers(tournoiId)
  return useMutation({
    mutationFn: ({ id, entree }: { id: number; entree: ModifierArcher }) =>
      modifierArcher(id, entree),
    onSuccess: invalider,
  })
}

export function useSupprimerArcher(tournoiId: number) {
  const invalider = useInvaliderArchers(tournoiId)
  return useMutation({
    mutationFn: (id: number) => supprimerArcher(id),
    onSuccess: invalider,
  })
}
