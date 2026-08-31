// Hooks React Query du palmarès (E06US004).
//
// Le palmarès est **vivant** : une fourchette « 1ᵉʳ-2ᵉ » se referme quand la finale tombe, et ces
// bascules viennent d'ailleurs que de l'écran courant. Le rafraîchissement **principal** est le
// canal live (`donnees_modifiees` post-commit → invalidation globale) ; le poll n'est qu'un
// **filet**. ⚠️ Intervalle **long**, pour la même raison qu'`useAffectations` (E07US008) : chaque
// appel refait la lecture la plus chère de l'application — classement complet **et** reconstruction
// de chaque tableau (`# DETTE-031`).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type ReglagePodiums, getPalmares, getReglagePodiums, putReglagePodiums } from './api'

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

const cleReglage = (tournoiId: number) => ['reglage-podiums', tournoiId] as const

// Le réglage, lui, ne bouge que sur geste de l'organisateur : **aucun poll**. Le payer au même
// rythme que le palmarès ferait une requête de plus toutes les 30 s pour une ligne qui ne change
// qu'à la demande.
export function useReglagePodiums(tournoiId: number) {
  return useQuery({
    queryKey: cleReglage(tournoiId),
    queryFn: () => getReglagePodiums(tournoiId),
  })
}

export function useReglerPodiums(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation<ReglagePodiums, Error, ReglagePodiums>({
    mutationFn: (reglage) => putReglagePodiums(tournoiId, reglage),
    onSuccess: (valeur) => {
      // ⚠️ **La réponse est POSÉE, pas seulement invalidée** — patron des dix autres mutations du
      // dépôt. `invalidateQueries` seule laisse `data` sur l'ancienne valeur pendant que le refetch
      // est en vol, or `isPending` est déjà retombé : le geste suivant se calculait alors sur un
      // réglage périmé et **perdait la portée qu'on venait d'enregistrer** (relevé en revue).
      queryClient.setQueryData(cleReglage(tournoiId), valeur)
      // Le palmarès aussi : ce sont ses blocs que le réglage vient de changer. Sans cela, l'écran
      // garderait les anciens podiums jusqu'au prochain poll (30 s).
      queryClient.invalidateQueries({ queryKey: ['palmares', tournoiId] })
    },
  })
}
