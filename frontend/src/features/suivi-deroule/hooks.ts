// Hooks React Query du suivi du déroulé (E07US004, ADR-0064).
//
// **Poll court**, comme la console de supervision et pour la même raison de fond (ADR-0038 §4) : le
// suivi ne bouge pas seulement quand une écriture survient (un duel tranché → `donnees_modifiees` →
// invalidation globale), il bouge aussi *parce que le temps passe* — l'écran de salle doit se
// rafraîchir même si le serveur n'a rien à dire, ne serait-ce que pour survivre à un événement
// WebSocket manqué pendant une coupure. Un écran projeté qui se fige sur un état ancien **ne se
// plaint pas** : c'est précisément le mode de panne que le CA veut éviter.

import { useQuery } from '@tanstack/react-query'

import { getSuiviDeroule } from './api'

/** ~10 s : le suivi est au grain du **tour**, pas de la flèche — il n'a pas besoin d'être nerveux,
 * et chaque tick reconstruit les tableaux des phases en tableau côté serveur. */
const INTERVALLE_POLL_MS = 10000

const cleSuivi = (departId: number | null) => ['suivi-deroule', departId] as const

/** Le suivi du **créneau** désigné. `null` tant qu'aucun n'est choisi : la requête est alors
 * désactivée plutôt que lancée sur un identifiant inventé (ADR-0075). */
export function useSuiviDeroule(departId: number | null) {
  return useQuery({
    queryKey: cleSuivi(departId),
    queryFn: () => getSuiviDeroule(departId as number),
    enabled: departId !== null,
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}
