// Hooks React Query de la feature « placement » (E03US004, ADR-0024).
//
// Le plan de cibles d'un départ est de l'état **serveur** (lecture) ; régénérer, déplacer et placer
// les restants sont des **mutations** qui invalident ce plan (rafraîchissement immédiat, en plus de
// la diffusion temps réel post-commit côté serveur, qui invalide tout le cache).
//
// Particularité de cette US : le drag cible une **inscription**, mais le plan ne porte que des
// `archer_id`. Le backend n'expose pas la liste des inscriptions d'un départ ; on la reconstitue en
// interrogeant, pour chaque archer présent dans le plan, ses inscriptions (`useInscriptionParArcher`).

import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { getInscriptions } from '../inscriptions/api'
import {
  type Destination,
  deplacerInscription,
  getPlanDeCibles,
  placerRestants,
  regenererPlan,
} from './api'

const clePlan = (tournoiId: number, departId: number) =>
  ['plan-de-cibles', tournoiId, departId] as const

export function usePlanDeCibles(tournoiId: number, departId: number) {
  return useQuery({
    queryKey: clePlan(tournoiId, departId),
    queryFn: () => getPlanDeCibles(tournoiId, departId),
  })
}

export function useRegenerer(tournoiId: number, departId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => regenererPlan(tournoiId, departId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePlan(tournoiId, departId) }),
  })
}

export function useDeplacer(tournoiId: number, departId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      inscriptionId,
      destination,
    }: {
      inscriptionId: number
      destination: Destination
    }) => deplacerInscription(tournoiId, departId, inscriptionId, destination),
    // `onSettled` et non `onSuccess` : un 409 `deplacement_invalide` laisse l'état serveur
    // inchangé, mais on refetch quand même pour **réconcilier** l'affichage (le plan reste la
    // vérité serveur, jamais l'optimisme du drag).
    onSettled: () => queryClient.invalidateQueries({ queryKey: clePlan(tournoiId, departId) }),
  })
}

export function usePlacerRestants(tournoiId: number, departId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => placerRestants(tournoiId, departId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePlan(tournoiId, departId) }),
  })
}

// Reconstitue la correspondance `archer_id → inscription_id` **pour ce départ**. Faute d'endpoint
// listant les inscriptions d'un départ (manque backend, cf. rapport d'US), on interroge en
// parallèle les inscriptions de chaque archer du plan, puis on retient celle du départ courant. La
// clé de requête est partagée avec la feature « inscriptions » (cache mutualisé, invalidé de même).
export function useInscriptionParArcher(
  departId: number,
  archerIds: number[],
): Map<number, number> {
  const resultats = useQueries({
    queries: archerIds.map((archerId) => ({
      queryKey: ['inscriptions', archerId] as const,
      queryFn: () => getInscriptions(archerId),
    })),
  })

  const map = new Map<number, number>()
  resultats.forEach((resultat, i) => {
    const archerId = archerIds[i]
    if (archerId === undefined) return
    const inscription = resultat.data?.find((ins) => ins.depart_id === departId)
    if (inscription) map.set(archerId, inscription.id)
  })
  return map
}
