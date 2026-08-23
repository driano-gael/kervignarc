// Hooks React Query des **jalons « prêt à… »** (E16US012).
//
// Lecture **live** par poll court, comme la complétude (E12US005) et la supervision (E12US001) : ce
// qu'un jalon liste bouge au fil des inscriptions, des créneaux ajoutés et des séries validées —
// autant d'écritures qui vivent dans d'autres features et n'ont aucune raison de connaître cette
// clé de cache. `staleTime: 0` surcharge le `staleTime` global (30 s, inadapté à un écran de
// suivi) : sans lui, l'écran pouvait annoncer « il manque des inscrits » après que le compte était
// bon — exactement le défaut que `useExigenceEffectif` avait déjà eu à corriger.

import { useQuery } from '@tanstack/react-query'
import { getPreparationJalon, type Jalon } from './api'

const INTERVALLE_POLL_MS = 5000

// La clé porte le **membre** : deux jalons du même tournoi sont deux réponses distinctes.
export const clePreparationJalon = (tournoiId: number, jalon: Jalon) =>
  ['jalon', tournoiId, jalon] as const

// `actif` **coupe le poll** quand la question ne se pose plus (tournoi déjà lancé, annulé) : sans
// lui, chaque tablette laissée sur l'écran interrogeait le serveur toutes les 5 s pour une réponse
// dont plus rien n'était affiché (relevé en revue). Le défaut est `true` : un jalon se lit en
// continu, c'est le cas nominal.
export function usePreparationJalon(tournoiId: number, jalon: Jalon, actif = true) {
  return useQuery({
    queryKey: clePreparationJalon(tournoiId, jalon),
    queryFn: () => getPreparationJalon(tournoiId, jalon),
    refetchInterval: INTERVALLE_POLL_MS,
    staleTime: 0,
    enabled: actif,
  })
}
