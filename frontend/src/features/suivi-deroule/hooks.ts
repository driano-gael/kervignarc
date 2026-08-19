// Hooks React Query du suivi du déroulé (E07US004, ADR-0064).
//
// **Poll court**, comme la console de supervision et pour la même raison de fond (ADR-0038 §4) : le
// suivi ne bouge pas seulement quand une écriture survient (un duel tranché → `donnees_modifiees` →
// invalidation globale), il bouge aussi *parce que le temps passe* — l'écran de salle doit se
// rafraîchir même si le serveur n'a rien à dire, ne serait-ce que pour survivre à un événement
// WebSocket manqué pendant une coupure. Un écran projeté qui se fige sur un état ancien **ne se
// plaint pas** : c'est précisément le mode de panne que le CA veut éviter.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getArretsEnAttente, getSuiviDeroule, relancerArret } from './api'

/** ~10 s : le suivi est au grain du **tour**, pas de la flèche — il n'a pas besoin d'être nerveux,
 * et chaque tick reconstruit les tableaux des phases en tableau côté serveur. */
const INTERVALLE_POLL_MS = 10000

export const RACINE_SUIVI = ['suivi-deroule'] as const
const cleSuivi = (departId: number | null) => [...RACINE_SUIVI, departId] as const

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

// --- Arrêts programmés (E05US033, ADR-0091) -----------------------------------------------------

export const RACINE_ARRETS = ['arrets-en-attente'] as const

/**
 * Les arrêts qui **attendent une relance** dans ce créneau.
 *
 * ⚠️ **Même poll que le suivi, et pour la même raison** : un arrêt ne se franchit pas quand
 * l'organisateur clique, il se franchit quand un tour s'achève — donc à la faveur d'une validation
 * faite par un scoreur, ailleurs, sur une tablette. Sans poll, le pilotage n'apprendrait qu'une phase
 * est en pause qu'au prochain rechargement de page : c'est exactement le mode de panne neuf que
 * l'US cherche à éviter (la salle attend, personne ne sait pourquoi).
 */
export function useArretsEnAttente(departId: number | null) {
  return useQuery({
    queryKey: [...RACINE_ARRETS, departId] as const,
    queryFn: () => getArretsEnAttente(departId as number),
    enabled: departId !== null,
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

/**
 * Relance la salle pour **un** arrêt — donc pour toutes les phases qu'il a coupées.
 *
 * Invalide le suivi **et** la liste d'arrêts : les statuts de phase changent, et l'arrêt sort de la
 * liste. Ne pas invalider le suivi laisserait le schéma afficher « en pause » sur une phase repartie
 * pendant les dix secondes du poll suivant — l'organisateur cliquerait deux fois.
 */
export function useRelancerArret(departId: number | null) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (arretId: number) => relancerArret(departId as number, arretId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: RACINE_ARRETS })
      void client.invalidateQueries({ queryKey: RACINE_SUIVI })
    },
  })
}
