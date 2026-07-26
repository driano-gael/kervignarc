// Hooks React Query de la feature « archive » (E11US003).
//
// Un téléchargement est une **action** ponctuelle (pas de l'état serveur à mettre en cache) →
// `useMutation`. `isPending` désactive le bouton pendant la génération (l'archive peut être lourde :
// snapshot + PDF) ; `error` alimente `MessageErreur`.

import { useMutation } from '@tanstack/react-query'
import { type OptionsArchive, telechargerArchive } from './api'

export function useTelechargerArchive(tournoiId: number) {
  return useMutation({
    mutationFn: (options: OptionsArchive) => telechargerArchive(tournoiId, options),
  })
}
