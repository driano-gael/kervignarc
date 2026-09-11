// Cas d'usage React Query de la surface scoreur de qualification (E16US019).
//
// Les deux mutations renvoient la série à jour : on **pose** le résultat dans le cache plutôt que
// de le réinvalider aussitôt — le serveur vient de rendre l'état autoritaire. Le classement, lui,
// est invalidé : une revalidation après correction change le total. La clé de série est celle de la
// feature `saisie`, **importée** et non recopiée (une clé qui diverge n'invalide plus rien, et rien
// ne rougit).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { Serie } from '../saisie/api'
import { cleSerie } from '../saisie/hooks'
import { nouvelIdentifiant } from '../saisie/volees'
import { cleClassement, INTERVALLE_POLL_MS } from '../competition/hooks'
import { annulerValidation, getSerieScoreur, refermerCorrection, validerSerie } from './api'

export function useSerieScoreur(tournoiId: number, archerId: number | null) {
  return useQuery({
    queryKey: cleSerie(tournoiId, archerId ?? 0, 'scoreur'),
    queryFn: () => {
      // `enabled` garantit le non-`null`, mais un `as number` ne le **dit** pas : on lève plutôt
      // que de mentir au compilateur (règle 4).
      if (archerId === null) throw new Error('Aucun archer choisi.')
      return getSerieScoreur(tournoiId, archerId)
    },
    enabled: archerId !== null,
    // La tablette écrit pendant que le scoreur regarde : sans relecture, il validerait un
    // affichage périmé. Même cadence que le classement (`competition/hooks.ts`).
    refetchInterval: INTERVALLE_POLL_MS,
  })
}

// ⚠️ L'identifiant d'idempotence est tiré **dans** `mutationFn`, donc deux appels du même geste
// portent deux clés et le registre serveur ne les dédoublonne pas. Le double-clic reste barré par
// `disabled={enCours}` ; le résidu est la fenêtre d'un rendu. Assumé plutôt que sur-construit : un
// identifiant stable par geste demanderait un état de plus dans le panneau, pour un coût réel d'une
// trace d'audit en double (validation) ou d'un 422 affiché (annulation). Relevé en revue.
export function useValiderSerie(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (archerId: number) => validerSerie(tournoiId, archerId, nouvelIdentifiant()),
    onSuccess: (serie: Serie) => {
      queryClient.setQueryData(cleSerie(tournoiId, serie.archer_id, 'scoreur'), serie)
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
    },
  })
}

export function useRefermerCorrection(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ archerId, numero }: { archerId: number; numero: number }) =>
      refermerCorrection(tournoiId, archerId, numero, nouvelIdentifiant()),
    onSuccess: (serie: Serie) => {
      queryClient.setQueryData(cleSerie(tournoiId, serie.archer_id, 'scoreur'), serie)
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
    },
  })
}

export function useAnnulerValidation(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ archerId, numero }: { archerId: number; numero: number }) =>
      annulerValidation(tournoiId, archerId, numero, nouvelIdentifiant()),
    // ⚠️ Le classement est invalidé **alors que le total ne bouge pas** (ADR-0109) : c'est
    // volontaire, l'annulation en change l'affichage (la feuille passe « en correction ») sans en
    // changer les chiffres. Ne pas « optimiser » en le retirant.
    onSuccess: (serie: Serie) => {
      queryClient.setQueryData(cleSerie(tournoiId, serie.archer_id, 'scoreur'), serie)
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
    },
  })
}
