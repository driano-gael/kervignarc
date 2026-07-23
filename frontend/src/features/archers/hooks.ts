// Hooks React Query de la feature « archers » (E02US003).
//
// La liste des inscrits d'un tournoi est de l'état **serveur** (lecture) ; éditer et désinscrire
// sont des **mutations**. Chacune invalide deux caches : la liste elle-même, et le **classement**
// — un archer corrigé y change de nom, un archer désinscrit doit en disparaître. C'est en plus de
// la diffusion temps réel post-commit, qui invalide tout le cache ; l'invalidation locale est le
// filet quand le lien WebSocket est momentanément coupé.
//
// La dépendance va d'ici vers `competition` (on lui emprunte `cleClassement`) et jamais l'inverse :
// un import croisé entre deux modules de hooks serait un cycle.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cleClassement } from '../competition/hooks'
import {
  fusionnerArchers,
  getArchers,
  getDoublons,
  type ModifierArcher,
  modifierArcher,
  supprimerArcher,
} from './api'

const cleArchers = (tournoiId: number) => ['archers', tournoiId] as const
const cleDoublons = (tournoiId: number) => ['doublons', tournoiId] as const

// `enabled` (défaut `true`) permet à un appelant monté en permanence — la recherche de la sidebar
// admin (E12US006) — de ne déclencher le fetch qu'une fois l'utilisateur en demande, sans changer le
// comportement des écrans existants. Même idiome que `useImpactRegeneration(..., actif)`.
export function useArchers(tournoiId: number, enabled = true) {
  return useQuery({
    queryKey: cleArchers(tournoiId),
    queryFn: () => getArchers(tournoiId),
    enabled,
  })
}

function useInvaliderArchers(tournoiId: number) {
  const queryClient = useQueryClient()
  return async () => {
    await queryClient.invalidateQueries({ queryKey: cleArchers(tournoiId) })
    await queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
    // La détection de doublons dérive de la liste des inscrits : une édition, une désinscription ou
    // une fusion peut la changer (une fusion en retire une paire ; une édition peut en créer ou en
    // défaire une). On l'invalide avec le reste plutôt que de la laisser afficher un état périmé.
    await queryClient.invalidateQueries({ queryKey: cleDoublons(tournoiId) })
  }
}

// La détection est de l'état **serveur**. L'écran « Doublons » n'est monté que lorsqu'on ouvre sa
// destination (`courant && <Doublons/>`), donc la requête ne part pas tant qu'il est fermé — la
// paresse vient de là, pas du fetch. `enabled` reste offert par symétrie avec `useArchers` (E12US006),
// pour un futur appelant monté en permanence qui voudrait, lui, différer le fetch.
export function useDoublons(tournoiId: number, enabled = true) {
  return useQuery({
    queryKey: cleDoublons(tournoiId),
    queryFn: () => getDoublons(tournoiId),
    enabled,
  })
}

export function useModifierArcher(tournoiId: number) {
  const invalider = useInvaliderArchers(tournoiId)
  return useMutation({
    mutationFn: ({ id, entree }: { id: number; entree: ModifierArcher }) =>
      modifierArcher(id, entree),
    onSuccess: invalider,
  })
}

export function useSupprimerArcher(tournoiId: number) {
  const invalider = useInvaliderArchers(tournoiId)
  return useMutation({
    mutationFn: ({ id, autoriserSuppressionEngage = false }: SupprimerArcherVariables) =>
      supprimerArcher(id, autoriserSuppressionEngage),
    onSuccess: invalider,
  })
}

export function useFusionnerArchers(tournoiId: number) {
  const invalider = useInvaliderArchers(tournoiId)
  return useMutation({
    mutationFn: ({ gagnantId, perdantId }: { gagnantId: number; perdantId: number }) =>
      fusionnerArchers(gagnantId, perdantId),
    onSuccess: invalider,
  })
}

interface SupprimerArcherVariables {
  id: number
  // Confirmation après un 409 `archer_engage` : efface aussi les scores et le placement.
  autoriserSuppressionEngage?: boolean
}
