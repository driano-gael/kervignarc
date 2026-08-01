// Hooks React Query de la feature « composer un déroulé » (E01US024).
//
// Le **diagnostic** est de l'état serveur dérivé de deux choses : le format enregistré et
// l'effectif simulé. Il entre donc dans la clé de cache — changer N ne « rafraîchit » pas le
// diagnostic, il en demande un **autre**. C'est ce qui rend le CA « changer N recalcule le dessin »
// gratuit : React Query sert le dessin déjà vu quand on revient à 120 après un détour par 82.
//
// La **simulation** est une mutation et non une query, bien qu'elle ne change rien en base : elle
// joue plusieurs milliers de volées, on ne la déclenche pas au montage ni au refocus. `POST` traduit
// exactement cela — « fais ce calcul maintenant, parce que je te le demande ».

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { NouveauFormat } from '../patrimoine/api'
import { useModifierFormat } from '../patrimoine/hooks'
import { getDiagnostic, simulerFormat, type Diagnostic, type SimulationFormat } from './api'

// Préfixe **commun** à tous les diagnostics, quel que soit l'effectif. C'est lui qu'on invalide
// après un enregistrement : le brouillon a changé, donc **tous** les effectifs déjà calculés sont
// périmés, pas seulement celui affiché.
export const cleDiagnostics = ['deroule', 'diagnostic'] as const

export const cleDiagnostic = (formatId: number, effectif: number | null) =>
  [...cleDiagnostics, formatId, effectif] as const

export function useDiagnostic(formatId: number, effectif: number | null) {
  return useQuery<Diagnostic>({
    queryKey: cleDiagnostic(formatId, effectif),
    queryFn: () => getDiagnostic(formatId, effectif),
  })
}

/**
 * Enregistre le brouillon **et** périme le schéma.
 *
 * ⚠️ `useModifierFormat` seul ne suffit pas : il invalide `['patrimoine', 'formats']`, sans aucun
 * recouvrement de préfixe avec la clé du diagnostic. Avec `staleTime: 30_000`,
 * `refetchOnWindowFocus: false` et un composant qui ne remonte pas, la query ne refetchait **ni**
 * par invalidation **ni** par péremption : le schéma restait figé sur la version d'avant, pendant
 * que l'écran retirait l'avertissement « modifications non enregistrées ». Il affirmait donc être
 * à jour tout en montrant le passé — et le bouton « Simuler » restait verrouillé sur un
 * `applicable` périmé.
 */
export function useEnregistrerBrouillon() {
  const queryClient = useQueryClient()
  const enregistrer = useModifierFormat()
  return {
    ...enregistrer,
    enregistrer: (
      variables: { id: number; entree: NouveauFormat },
      options?: { onSuccess?: () => void },
    ) =>
      enregistrer.mutate(variables, {
        onSuccess: () => {
          void queryClient.invalidateQueries({ queryKey: cleDiagnostics })
          options?.onSuccess?.()
        },
      }),
  }
}

export function useSimulerFormat(formatId: number) {
  const queryClient = useQueryClient()
  return useMutation<SimulationFormat, Error, number>({
    mutationFn: (effectif: number) => simulerFormat(formatId, effectif),
    // La simulation renvoie le diagnostic **au même effectif** : on le verse dans le cache plutôt
    // que de laisser l'écran en redemander un identique au serveur.
    onSuccess: (resultat) => {
      queryClient.setQueryData(
        cleDiagnostic(resultat.format_id, resultat.effectif),
        resultat.diagnostic,
      )
    },
  })
}
