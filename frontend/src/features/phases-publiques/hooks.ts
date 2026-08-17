// Hooks React Query de l'index des phases publiques (E05US031).//
// `# DETTE-031` — cette lecture **recompose la phase entière à chaque appel**, chaîne amont
// comprise. Depuis E05US031 elle est servie au **public** et à l'écran de salle : la charge n'est
// plus bornée par le nombre de postes de travail mais par le nombre de spectateurs. Aggravé par
// `shared/realtime/useRealtime`, qui invalide **sans clé** — chaque score validé refetch tout, chez
// tout le monde. Cf. le registre : la résorption est une mémoïsation par `(tournoi_id, version)`,
// pas un cache posé au jugé.

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
