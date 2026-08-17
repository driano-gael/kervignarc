// Hooks React Query de l'index des phases publiques (E05US031).

import { useQuery } from '@tanstack/react-query'

import { getPhasesPubliques } from './api'

export function clePhasesPubliques(departId: number) {
  return ['phases-publiques', departId] as const
}

/** Les phases d'un créneau, ordonnées, avec leur statut. `departId` peut être `null` le temps que la
 * liste des créneaux arrive. */
export function usePhasesPubliques(departId: number | null) {
  return useQuery({
    queryKey: clePhasesPubliques(departId ?? 0),
    queryFn: () => getPhasesPubliques(departId as number),
    enabled: departId !== null,
    // Même parti que les autres lectures publiques : un refetch au focus n'apporte rien sur un
    // écran de consultation, et l'appli publique reste ouverte des heures sur un téléphone.
    refetchOnWindowFocus: false,
  })
}
