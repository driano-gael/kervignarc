// Hooks React Query de la complétude du tournoi (E12US005).
//
// Lecture **live** par poll court, comme la supervision (E12US001) : la complétude bouge au fil des
// validations de séries et des marquages de paiement, qui n'émettent pas tous un événement dédié — le
// `refetchInterval` capte l'avancement sans dépendre d'une diffusion. `staleTime: 0` surcharge le
// `staleTime` global (30 s, inadapté à un écran de suivi). Le passage à *terminé* réutilise la
// mutation de `competition` (une seule voie d'écriture du cycle de vie) et ré-invalide la complétude.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { terminerTournoi } from '../competition/api'
import { CLE_TOURNOIS } from '../competition/hooks'
import { getCompletude } from './api'

const INTERVALLE_POLL_MS = 5000

// Exportée depuis E16US003 : la complétude est désormais lue par **trois** endroits hors de cette
// feature (accueil, frise du cycle de vie, écran Paiements), dont un qui doit l'**invalider** après
// un marquage de paiement. Un littéral `['completude', id]` recopié dans chaque appelant se serait
// désynchronisé au premier changement de clé — et l'un d'eux (`FriseCycleDeVie`) l'avait déjà recopié.
export const cleCompletude = (tournoiId: number) => ['completude', tournoiId] as const

export function useCompletude(tournoiId: number) {
  return useQuery({
    queryKey: cleCompletude(tournoiId),
    queryFn: () => getCompletude(tournoiId),
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

export function useTerminerDepuisCompletude(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => terminerTournoi(tournoiId),
    onSuccess: () => {
      // La liste des tournois (statut → badge, accueil contextualisé) **et** la complétude (le
      // bouton disparaît, l'écran reflète l'état figé) se resynchronisent.
      queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS })
      queryClient.invalidateQueries({ queryKey: cleCompletude(tournoiId) })
    },
  })
}
