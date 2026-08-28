// Hooks React Query du pilotage d'un tour (E12US002, ADR-0056).
//
// Le feu vert est **live** : un duel devient prêt dès que sa source est validée par un scoreur, ou
// bloqué si le classement change. Un poll court (comme la supervision, E12US001) capte ces bascules
// — la diffusion WebSocket du lancement ne suffit pas, car ce sont les **validations de duels** (un
// autre flux) qui font avancer le tableau. `staleTime: 0` surcharge le staleTime global (écran live).
// Le lancement est une **mutation** qui ré-invalide feu vert + impact.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { declarerForfaitDuel } from '../forfaits/api'
import { cleTableau } from '../saisie-duels/hooks'
import { getFeuVert, getImpactLancement, lancerTour } from './api'

const INTERVALLE_POLL_MS = 5000

const cleFeuVert = (tournoiId: number, phaseId: number) => ['feu-vert', tournoiId, phaseId] as const
const cleImpact = (tournoiId: number, phaseId: number) =>
  ['impact-lancement', tournoiId, phaseId] as const

export function useFeuVert(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleFeuVert(tournoiId, phaseId ?? 0),
    queryFn: () => getFeuVert(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

export function useImpactLancement(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleImpact(tournoiId, phaseId ?? 0),
    queryFn: () => getImpactLancement(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

export function useLancerTour(tournoiId: number, phaseId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => lancerTour(tournoiId, phaseId as number),
    onSuccess: () => {
      if (phaseId === null) return
      queryClient.invalidateQueries({ queryKey: cleFeuVert(tournoiId, phaseId) })
      queryClient.invalidateQueries({ queryKey: cleImpact(tournoiId, phaseId) })
    },
  })
}

// Le forfait déclaré **depuis le feu vert** (E16US008) : portée `'admin'`, car c'est l'organisateur
// qui agit, et invalidation des deux vues de l'écran — sans quoi la ligne resterait bloquée jusqu'au
// prochain poll (5 s) alors qu'on vient de la débloquer.
export function useDeclarerForfaitDepuisFeuVert(tournoiId: number, phaseId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (archerId: number) =>
      declarerForfaitDuel(tournoiId, phaseId as number, archerId, 'abandon', undefined, 'admin'),
    onSuccess: () => {
      if (phaseId === null) return
      queryClient.invalidateQueries({ queryKey: cleFeuVert(tournoiId, phaseId) })
      queryClient.invalidateQueries({ queryKey: cleImpact(tournoiId, phaseId) })
      // ⚠️ Le tableau aussi : la ligne porte un renvoi vers « Plan de duels », et l'organisateur y
      // lirait un tableau d'avant le walkover. Clé importée de `saisie-duels`, propriétaire de la
      // query — une invalidation qui rate sa clé ne casse rien de VISIBLE, elle se contente de
      // laisser le tableau périmé, donc rien ne rougirait si elle divergeait.
      queryClient.invalidateQueries({ queryKey: cleTableau(tournoiId, phaseId) })
    },
  })
}
