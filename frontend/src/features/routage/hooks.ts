// Hooks React Query du panneau de routage (E04US018).
//
// Le panneau est **live** : la cible se fige au lancement du tour, l'adversaire se révèle quand le
// duel amont est validé — deux bascules qui viennent d'ailleurs que de l'écran courant. Le
// rafraîchissement principal est le canal live ; le poll n'est qu'un **filet**, d'où un intervalle
// **long** : cet écran tourne sur ~30 tablettes au moment de charge maximale, et chaque appel
// refait la lecture la plus chère de l'application. ⚠️ La clé de cache inclut la **liste
// d'archers** : sans elle, deux panneaux ouverts sur deux cibles se voleraient leur cache.

import { useQuery } from '@tanstack/react-query'
import { getAffectations, getRoutage } from './api'

const INTERVALLE_POLL_MS = 20000

const cleRoutage = (departId: number | null, archerIds: number[], phaseId: number | null) =>
  ['routage', departId, phaseId, archerIds.join(',')] as const

const cleAffectations = (departId: number | null, phaseId: number | null) =>
  ['routage', 'affectations', departId, phaseId] as const

/** Le routage **d'un créneau** (ADR-0075) : « le tableau qui vient » n'existe que dans une
 * séquence. `null` tant qu'aucun créneau n'est résolu — la requête est alors désactivée. */
export function useRoutage(
  departId: number | null,
  archerIds: number[],
  phaseId: number | null = null,
) {
  return useQuery({
    queryKey: cleRoutage(departId, archerIds, phaseId),
    queryFn: () => getRoutage(departId as number, archerIds, phaseId),
    // Aucun archer à router — ou aucun créneau résolu : pas de requête. (Panneau fermé = composant
    // **démonté** par les deux appelants.)
    enabled: departId !== null && archerIds.length > 0,
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

// Toutes les affectations du tableau (E07US008) — la vue publique et l'écran de salle.
//
// Pas de liste d'archers dans la clé : la lecture est la **même pour tout le monde**, donc une
// seule entrée de cache par appareil sert toutes les cartes suivies. ⚠️ Le gain s'arrête à
// l'appareil — le cache React Query est **par navigateur**, il n'existe ni cache serveur ni en-tête
// HTTP —, et `useRealtime` invalidant **sans clé**, chaque écriture serveur refetch tous les
// clients montés. C'est `# DETTE-031`, que cette US aggrave. D'où `actif` : les appelants qui n'ont
// rien à afficher ne montent pas la requête.
export function useAffectations(
  departId: number | null,
  phaseId: number | null = null,
  actif = true,
) {
  return useQuery({
    queryKey: cleAffectations(departId, phaseId),
    queryFn: () => getAffectations(departId as number, phaseId),
    enabled: actif && departId !== null,
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}
