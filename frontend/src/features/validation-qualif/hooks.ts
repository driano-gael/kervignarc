// Cas d'usage React Query de la surface scoreur de qualification (E16US019).
//
// Les trois mutations renvoient la série à jour : on **pose** le résultat dans le cache plutôt que
// de le réinvalider aussitôt — le serveur vient de rendre l'état autoritaire. Classement et file
// sont invalidés. La clé de série **étend** celle de la feature `saisie` (le créneau en plus,
// E04US019) sans la recopier : une clé qui diverge n'invalide plus rien, et rien ne rougit.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { Serie } from '../saisie/api'
import { cleSerie } from '../saisie/hooks'
import { nouvelIdentifiant } from '../saisie/volees'
import { cleClassement, INTERVALLE_POLL_MS } from '../competition/hooks'
import {
  annulerValidation,
  getFileScoreur,
  getSerieScoreur,
  refermerCorrection,
  validerSerie,
} from './api'

interface GesteSurVolee {
  archerId: number
  numero: number
  departId: number | null
}

export const cleFileScoreur = (tournoiId: number, departId?: number | null) =>
  departId === undefined ? ['file-scoreur', tournoiId] : ['file-scoreur', tournoiId, departId]

export function useFileScoreur(tournoiId: number, departId: number | null) {
  return useQuery({
    queryKey: cleFileScoreur(tournoiId, departId),
    queryFn: () => {
      if (departId === null) throw new Error('Aucun créneau choisi.')
      return getFileScoreur(tournoiId, departId)
    },
    enabled: departId !== null,
    // Filet du WebSocket (qui invalide tout le cache à chaque écriture) : sans lui, une coupure
    // du direct figerait la file et l'attente affichée.
    refetchInterval: INTERVALLE_POLL_MS,
  })
}

// La feuille vue par le scoreur dépend du créneau : changer de créneau doit la relire (E04US019).
const cleSerieScoreur = (tournoiId: number, archerId: number, departId: number | null) => [
  ...cleSerie(tournoiId, archerId, 'scoreur'),
  departId,
]

export function useSerieScoreur(
  tournoiId: number,
  archerId: number | null,
  departId: number | null,
) {
  return useQuery({
    queryKey: cleSerieScoreur(tournoiId, archerId ?? 0, departId),
    queryFn: () => {
      // `enabled` garantit le non-`null`, mais un `as number` ne le **dit** pas : on lève plutôt
      // que de mentir au compilateur (règle 4).
      if (archerId === null) throw new Error('Aucun archer choisi.')
      return getSerieScoreur(tournoiId, archerId, departId)
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
    mutationFn: ({ archerId, departId }: { archerId: number; departId: number | null }) =>
      validerSerie(tournoiId, archerId, departId, nouvelIdentifiant()),
    onSuccess: (serie: Serie, { departId }) => {
      queryClient.setQueryData(cleSerieScoreur(tournoiId, serie.archer_id, departId), serie)
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
      void queryClient.invalidateQueries({ queryKey: cleFileScoreur(tournoiId) })
    },
  })
}

export function useRefermerCorrection(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ archerId, numero, departId }: GesteSurVolee) =>
      refermerCorrection(tournoiId, archerId, numero, departId, nouvelIdentifiant()),
    onSuccess: (serie: Serie, { departId }) => {
      queryClient.setQueryData(cleSerieScoreur(tournoiId, serie.archer_id, departId), serie)
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
      void queryClient.invalidateQueries({ queryKey: cleFileScoreur(tournoiId) })
    },
  })
}

export function useAnnulerValidation(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ archerId, numero, departId }: GesteSurVolee) =>
      annulerValidation(tournoiId, archerId, numero, departId, nouvelIdentifiant()),
    // ⚠️ Le classement est invalidé **alors que le total ne bouge pas** (ADR-0109) : c'est
    // volontaire, l'annulation en change l'affichage (la feuille passe « en correction ») sans en
    // changer les chiffres. Ne pas « optimiser » en le retirant.
    // Au grain « toutes les N », annuler ouvre une correction : l'archer **sort** de la file.
    onSuccess: (serie: Serie, { departId }) => {
      queryClient.setQueryData(cleSerieScoreur(tournoiId, serie.archer_id, departId), serie)
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
      void queryClient.invalidateQueries({ queryKey: cleFileScoreur(tournoiId) })
    },
  })
}
