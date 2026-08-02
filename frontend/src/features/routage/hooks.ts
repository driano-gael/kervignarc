// Hooks React Query du panneau de routage (E04US018).
//
// Le panneau est **live** : la cible d'un archer se fige au moment où l'organisateur lance le tour
// (`LiveEvent('tour_lance')`, E12US002), et son adversaire se révèle quand le duel amont est validé
// par un autre scoreur. Ces deux bascules viennent d'ailleurs que de l'écran courant.
//
// Le rafraîchissement **principal** est le canal live : toute écriture serveur publie un
// `donnees_modifiees` post-commit, que `useRealtime` traduit en invalidation globale — le panneau
// se remet à jour tout seul, sans poll. Le poll n'est qu'un **filet** (WebSocket tombé, événement
// manqué), d'où un intervalle **long** : contrairement au feu vert (E12US002) ou à la supervision
// (E12US001), qui sont des écrans d'administration en un exemplaire, celui-ci tourne sur ~30
// tablettes à la fois, au moment de charge maximale, et chaque appel refait la lecture la plus
// chère de l'application (classement + reconstruction de l'arbre + plan de duels). `staleTime: 0`
// reste : c'est un écran vivant, pas une fiche.
//
// Attention : la clé de cache inclut la **liste d'archers**, pas seulement le tournoi. Sans elle,
// deux panneaux ouverts sur deux cibles se voleraient leur cache — le poste B afficherait les
// destinations du poste A.

import { useQuery } from '@tanstack/react-query'
import { getAffectations, getRoutage } from './api'

const INTERVALLE_POLL_MS = 20000

const cleRoutage = (tournoiId: number, archerIds: number[], phaseId: number | null) =>
  ['routage', tournoiId, phaseId, archerIds.join(',')] as const

const cleAffectations = (tournoiId: number, phaseId: number | null) =>
  ['routage', 'affectations', tournoiId, phaseId] as const

export function useRoutage(tournoiId: number, archerIds: number[], phaseId: number | null = null) {
  return useQuery({
    queryKey: cleRoutage(tournoiId, archerIds, phaseId),
    queryFn: () => getRoutage(tournoiId, archerIds, phaseId),
    // Aucun archer à router : pas de requête. (Panneau fermé = composant **démonté** par les deux
    // appelants — inutile d'ajouter un drapeau `actif` qui ne serait jamais passé à `false`.)
    enabled: archerIds.length > 0,
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

// Toutes les affectations du tableau (E07US008) — la vue publique et l'écran de salle.
//
// Pas de liste d'archers dans la clé, et c'est justement ce qui change : cette lecture est la
// **même pour tout le monde**, donc une seule entrée de cache sert les ~30 tablettes, les téléphones
// et les écrans de salle du gymnase. C'est aussi pourquoi elle peut se permettre le même filet de
// 20 s sans multiplier la lecture la plus chère de l'application par le nombre de spectateurs.
export function useAffectations(tournoiId: number, phaseId: number | null = null) {
  return useQuery({
    queryKey: cleAffectations(tournoiId, phaseId),
    queryFn: () => getAffectations(tournoiId, phaseId),
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}
