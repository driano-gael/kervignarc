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

import { getDiagnostic, simulerFormat, type Diagnostic, type SimulationFormat } from './api'

export const cleDiagnostic = (formatId: number, effectif: number | null) =>
  ['deroule', 'diagnostic', formatId, effectif] as const

export function useDiagnostic(formatId: number | null, effectif: number | null) {
  return useQuery<Diagnostic>({
    queryKey: cleDiagnostic(formatId ?? 0, effectif),
    queryFn: () => getDiagnostic(formatId as number, effectif),
    enabled: formatId !== null,
  })
}

export function useSimulerFormat(formatId: number | null) {
  const queryClient = useQueryClient()
  return useMutation<SimulationFormat, Error, number>({
    mutationFn: (effectif: number) => simulerFormat(formatId as number, effectif),
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
