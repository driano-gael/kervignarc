// Hooks React Query de la feature « séquence de phases » (E05US001).
//
// La liste des phases d'un tournoi est de l'état **serveur** ; ajouter/éditer/réordonner/supprimer
// et les transitions de statut sont des **mutations** qui invalident cette liste. Le
// réordonnancement resynchronise en `onSettled` (succès **comme** échec 409) : on ne laisse jamais
// l'ordre optimiste du geste diverger de la vérité serveur (cf. `placement/hooks.ts`).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { cleClassement } from '../competition/hooks'
import {
  ajouterPhase,
  changerStatutPhase,
  type ConfigPhase,
  getAvancement,
  getPhases,
  modifierPhase,
  reordonnerPhases,
  supprimerPhase,
  type TransitionPhase,
} from './api'

// Deux caches pour deux mailles (ADR-0076) : le **déroulé** du tournoi, et l'**avancement** de
// chaque créneau. Une transition de statut ne change pas le déroulé ; éditer le déroulé change en
// revanche ce que tous les créneaux affichent — d'où l'invalidation croisée ci-dessous.
const clePhases = (tournoiId: number) => ['phases', tournoiId] as const
const cleAvancement = (departId: number) => ['avancement-phases', departId] as const

export function usePhases(tournoiId: number) {
  return useQuery({
    queryKey: clePhases(tournoiId),
    queryFn: () => getPhases(tournoiId),
  })
}

// L'avancement d'un créneau. `departId` peut être `null` le temps que la liste des créneaux
// arrive : la requête est alors désactivée plutôt que lancée sur un identifiant inventé.
export function useAvancementPhases(departId: number | null) {
  return useQuery({
    queryKey: cleAvancement(departId ?? 0),
    queryFn: () => getAvancement(departId as number),
    enabled: departId !== null,
  })
}

export function useAjouterPhase(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (config: ConfigPhase) => ajouterPhase(tournoiId, config),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: clePhases(tournoiId) })
      // ⚠️ **Et l'avancement de tous les créneaux** (ADR-0076) : ils portent la définition
      // *assemblée*, donc éditer l'étape change ce que chacun affiche. Sans préfixe de départ, on
      // invalide la famille entière — il y a une poignée de créneaux, pas mille.
      void queryClient.invalidateQueries({ queryKey: ['avancement-phases'] })
      // ⚠️ **Le classement aussi.** `barrage_jusqu_au` vit sur la phase mais ne se **voit** que
      // dans le classement (égalités signalées). Sans cette invalidation, le cache de 30 s faisait
      // que régler le seuil puis revenir au classement n'affichait rien — le recetteur concluait à
      // un échec. Aucun événement temps réel n'est diffusé sur `PUT /phases`.
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
    },
  })
}

export function useModifierPhase(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ phaseId, config }: { phaseId: number; config: ConfigPhase }) =>
      modifierPhase(tournoiId, phaseId, config),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: clePhases(tournoiId) })
      // ⚠️ **Et l'avancement de tous les créneaux** (ADR-0076) : ils portent la définition
      // *assemblée*, donc éditer l'étape change ce que chacun affiche. Sans préfixe de départ, on
      // invalide la famille entière — il y a une poignée de créneaux, pas mille.
      void queryClient.invalidateQueries({ queryKey: ['avancement-phases'] })
      // ⚠️ **Le classement aussi.** `barrage_jusqu_au` vit sur la phase mais ne se **voit** que
      // dans le classement (égalités signalées). Sans cette invalidation, le cache de 30 s faisait
      // que régler le seuil puis revenir au classement n'affichait rien — le recetteur concluait à
      // un échec. Aucun événement temps réel n'est diffusé sur `PUT /phases`.
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
    },
  })
}

export function useReordonnerPhases(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (phases: number[]) => reordonnerPhases(tournoiId, phases),
    // Resync même en cas de refus serveur (422/409) : l'ordre affiché reste la vérité serveur.
    // Les avancements suivent le rang de leur étape (le serveur les réaligne) : on les resynchronise
    // donc aussi, sans quoi un créneau afficherait l'ancien ordre jusqu'au prochain rechargement.
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: clePhases(tournoiId) })
      await queryClient.invalidateQueries({ queryKey: ['avancement-phases'] })
    },
  })
}

export function useSupprimerPhase(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (phaseId: number) => supprimerPhase(tournoiId, phaseId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: clePhases(tournoiId) })
      // ⚠️ **Et l'avancement de tous les créneaux** (ADR-0076) : ils portent la définition
      // *assemblée*, donc éditer l'étape change ce que chacun affiche. Sans préfixe de départ, on
      // invalide la famille entière — il y a une poignée de créneaux, pas mille.
      void queryClient.invalidateQueries({ queryKey: ['avancement-phases'] })
      // ⚠️ **Le classement aussi.** `barrage_jusqu_au` vit sur la phase mais ne se **voit** que
      // dans le classement (égalités signalées). Sans cette invalidation, le cache de 30 s faisait
      // que régler le seuil puis revenir au classement n'affichait rien — le recetteur concluait à
      // un échec. Aucun événement temps réel n'est diffusé sur `PUT /phases`.
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
    },
  })
}

// Le cycle de vie s'adresse à un **créneau** (ADR-0076) : c'est lui qui démarre, met en pause et
// termine ses phases — le créneau du matin peut être en duels pendant que celui de l'après-midi
// qualifie. `tournoiId` reste nécessaire pour invalider le classement, qui est indexé par tournoi.
export function useChangerStatutPhase(tournoiId: number, departId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ phaseId, transition }: { phaseId: number; transition: TransitionPhase }) =>
      changerStatutPhase(departId, phaseId, transition),
    onSuccess: () => {
      // Seul l'avancement de **ce** créneau bouge : le déroulé du tournoi, lui, n'a pas de statut.
      void queryClient.invalidateQueries({ queryKey: cleAvancement(departId) })
      // ⚠️ **Le classement aussi.** Terminer une qualification fige ce qui s'y lit, et le classement
      // est calculé, non stocké : sans cette invalidation, le cache de 30 s le laisserait afficher
      // l'état d'avant la transition. Aucun événement temps réel n'est diffusé sur cette route.
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
    },
  })
}
