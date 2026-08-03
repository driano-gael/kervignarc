// Hooks React Query du palmarès (E06US004).
//
// Le palmarès est **vivant** : il se resserre à chaque duel validé (une fourchette « 1ᵉʳ-2ᵉ » se
// referme sur « 1ᵉʳ » quand la finale tombe), et ces bascules viennent d'ailleurs que de l'écran
// courant. Le rafraîchissement **principal** est le canal live — toute écriture serveur publie un
// `donnees_modifiees` post-commit que `useRealtime` traduit en invalidation globale ; le poll n'est
// qu'un **filet** (WebSocket tombé, événement manqué).
//
// ⚠️ Intervalle **long**, pour la même raison qu'`useAffectations` (E07US008) : chaque appel refait
// la lecture la plus chère de l'application — classement complet **et** reconstruction de chaque
// tableau. C'est `# DETTE-031`, dont cette US ajoute un troisième consommateur ; la ligne du
// registre est élargie en conséquence.

import { useQuery } from '@tanstack/react-query'
import { getPalmares } from './api'

const INTERVALLE_POLL_MS = 30000

const clePalmares = (tournoiId: number, categorieId?: number) =>
  ['palmares', tournoiId, categorieId ?? null] as const

export function usePalmares(tournoiId: number, categorieId?: number) {
  return useQuery({
    queryKey: clePalmares(tournoiId, categorieId),
    queryFn: () => getPalmares(tournoiId, categorieId),
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}
