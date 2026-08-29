// Hooks React Query des **jalons « prêt à… »** (E16US012).
//
// Lecture **live** par poll court, comme la complétude (E12US005) et la supervision (E12US001) : ce
// qu'un jalon liste bouge au fil des inscriptions, des créneaux ajoutés et des séries validées —
// autant d'écritures qui vivent dans d'autres features et n'ont aucune raison de connaître cette
// clé de cache. `staleTime: 0` surcharge le `staleTime` global (30 s, inadapté à un écran de
// suivi) : sans lui, l'écran pouvait annoncer « il manque des inscrits » après que le compte était
// bon — exactement le défaut que `useExigenceEffectif` avait déjà eu à corriger.

import { useQuery } from '@tanstack/react-query'
import { getApercusJalon, getPreparationJalon, type Jalon } from './api'

const INTERVALLE_POLL_MS = 5000

// La clé porte le **membre** : deux jalons du même tournoi sont deux réponses distinctes.
export const clePreparationJalon = (tournoiId: number, jalon: Jalon) =>
  ['jalon', tournoiId, jalon] as const

// ⚠️ **Le poll ne se coupe pas selon le statut**, et c'est un retour assumé sur un correctif de la
// 1ʳᵉ passe de revue. Le couper supposait de savoir, côté front, quand la question cesse de se
// poser — donc d'y recopier la table des transitions, ce qui a produit un défaut plus grave que
// celui que la coupure évitait (2ᵉ passe, axe D). C'est désormais la **réponse** qui dit qu'il n'y
// a plus rien à préparer, et elle continue donc de servir. Le coût réel est nul : un écran
// d'administration, ouvert par une personne, sur un tournoi déjà lancé.
export function usePreparationJalon(tournoiId: number, jalon: Jalon) {
  return useQuery({
    queryKey: clePreparationJalon(tournoiId, jalon),
    queryFn: () => getPreparationJalon(tournoiId, jalon),
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
  })
}

export const cleApercusJalon = (jalon: Jalon) => ['jalons-apercu', jalon] as const

// ⚠️ **Pas de poll ici**, à la différence de `usePreparationJalon`. L'aperçu coiffe la **liste des
// tournois**, un écran de choix qu'on traverse — pas un écran de suivi ouvert pendant la journée.
// Le rafraîchissement au montage et au retour d'onglet suffit, et il évite de relire les créneaux
// et l'effectif de tous les tournois toutes les cinq secondes.
// ⚠️ `actif` n'est pas un confort : la liste des tournois est rendue **aussi sous la porte
// Public**, sans jeton admin. Sans ce garde, la route partirait en 401 à chaque affichage public.
export function useApercusJalon(jalon: Jalon, actif: boolean) {
  return useQuery({
    queryKey: cleApercusJalon(jalon),
    queryFn: () => getApercusJalon(jalon),
    enabled: actif,
  })
}
