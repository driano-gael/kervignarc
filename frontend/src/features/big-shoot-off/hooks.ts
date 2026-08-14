// Hooks React Query du **Big Shoot Off** (E05US028) — état serveur d'une phase.
//
// ⚠️ **Les mutations vivent ici**, contrairement aux poules — dont les rencontres s'écrivent par
// `features/saisie-duels` parce qu'elles *sont* des duels (ADR-0083 §7). Une volée collective n'a
// pas d'adversaire, donc pas de pavé de duel à emprunter.
//
// Les deux mutations **écrivent directement le cache** avec l'état renvoyé, au lieu d'invalider :
// la réponse *est* la photo complète et à jour, donc un aller-retour de plus ne ferait qu'ouvrir
// une fenêtre où l'écran montre un archer sorti comme encore en lice.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getEtatBigShootOff, saisirVolee, validerManche, type EtatBigShootOff } from './api'

/** La clé de cache de l'état d'une phase. Domiciliée **ici** : c'est cette feature qui l'écrit. */
export function cleBigShootOff(tournoiId: number, phaseId: number) {
  return ['big-shoot-off', tournoiId, phaseId] as const
}

/** L'état de la phase — scoreur, dans son tournoi. */
export function useEtatBigShootOff(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleBigShootOff(tournoiId, phaseId ?? 0),
    queryFn: () => getEtatBigShootOff(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    // Même parti que les poules et le tableau : un refus déterministe (409 phase non réglée) ne
    // gagne rien à être réessayé, et un refetch au focus écraserait une frappe en cours.
    retry: false,
    refetchOnWindowFocus: false,
  })
}

/** Saisit une volée d'un finaliste. */
export function useSaisirVolee(tournoiId: number, phaseId: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (corps: { archerId: number; numero: number; valeurs: string[] }) =>
      saisirVolee({ tournoiId, phaseId, ...corps }),
    onSuccess: (etat: EtatBigShootOff) =>
      client.setQueryData(cleBigShootOff(tournoiId, phaseId), etat),
  })
}

/** Valide la manche courante d'un finaliste — c'est elle qui entrera au classement. */
export function useValiderManche(tournoiId: number, phaseId: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (corps: { archerId: number }) => validerManche({ tournoiId, phaseId, ...corps }),
    onSuccess: (etat: EtatBigShootOff) =>
      client.setQueryData(cleBigShootOff(tournoiId, phaseId), etat),
  })
}
