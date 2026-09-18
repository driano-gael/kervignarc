// Hooks React Query de la feature « audit » (E16US016).
//
// Le journal est de l'état **serveur**, en lecture seule : aucune mutation ici, et c'est
// structurel — une trace ne s'édite pas (`api/v1/audit.py`).

import { useQuery } from '@tanstack/react-query'
import { getAudit } from './api'

const cleAudit = (tournoiId: number) => ['audit', tournoiId] as const

export function useAudit(tournoiId: number) {
  return useQuery({
    queryKey: cleAudit(tournoiId),
    queryFn: () => getAudit(tournoiId),
  })
}
