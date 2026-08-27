// Hooks React Query de la vue publique des tableaux (E07US005).
//
// **Live** au sens du CA : le rafraîchissement principal est le canal temps réel ; le poll n'est
// qu'un **filet**, d'où un intervalle long. ⚠️ `# DETTE-031`, que cette US **élargit** : chaque
// appel reconstruit intégralement chaque tableau, **une fois par phase**, sur une route publique,
// en autant d'exemplaires qu'il y a de spectateurs. ⚠️ **Ce qui limite la casse est le montage
// conditionnel du composant, pas un drapeau** — et depuis E16US004 cela ne borne plus l'endpoint :
// l'onglet « Suivi » monte `useTableauxDesDeparts` dès l'ouverture de l'appli.

import { useQueries, useQuery } from '@tanstack/react-query'
import { getTableaux } from './api'

const INTERVALLE_POLL_MS = 20000

const cleTableaux = (departId: number | null) => ['tableaux', departId] as const

/** Les arbres du **créneau** désigné. `null` tant qu'aucun n'est choisi : la requête est alors
 * désactivée plutôt que lancée sur un identifiant inventé (ADR-0075). */
export function useTableaux(departId: number | null) {
  return useQuery({
    queryKey: cleTableaux(departId),
    queryFn: () => getTableaux(departId as number),
    enabled: departId !== null,
    refetchInterval: INTERVALLE_POLL_MS,
    // Écran vivant, pas une fiche : ce qu'on relit doit être considéré périmé d'emblée.
    staleTime: 0,
  })
}

/** Les arbres de **plusieurs** créneaux à la fois (E16US004, récapitulatif de journée).
 *
 * Un archer appartient à **un** départ (ADR-0075) qui n'est pas forcément celui que la salle tire
 * : lire le seul créneau en cours amputait le récapitulatif d'un archer du matin. ⚠️ **La liste
 * passée doit rester celle des départs réellement concernés**, dérivée des plans déjà chargés —
 * chaque entrée est une reconstruction serveur complète (`# DETTE-031`), et c'est la seule borne.
 */
export function useTableauxDesDeparts(departIds: number[]) {
  return useQueries({
    queries: departIds.map((departId) => ({
      queryKey: cleTableaux(departId),
      queryFn: () => getTableaux(departId),
      refetchInterval: INTERVALLE_POLL_MS,
      staleTime: 0,
    })),
  })
}
