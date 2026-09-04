// Hooks React Query de la feature « scoreurs » (E10US003).
//
// La liste des scoreurs d'un tournoi est de l'état **serveur** (lecture admin) ; créer/renommer/
// supprimer sont des **mutations** qui invalident cette liste (rafraîchissement immédiat, en plus
// de la diffusion temps réel post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  creerScoreur,
  getQrScoreur,
  getScoreurs,
  modifierScoreur,
  type NouveauScoreur,
  supprimerScoreur,
  telechargerCartesScoreurs,
} from './api'

const cleScoreurs = (tournoiId: number) => ['scoreurs', tournoiId] as const
const cleQrScoreur = (tournoiId: number, code: string, scoreurId: number) =>
  ['qr-scoreur', tournoiId, code, scoreurId] as const

export function useScoreurs(tournoiId: number) {
  return useQuery({
    queryKey: cleScoreurs(tournoiId),
    queryFn: () => getScoreurs(tournoiId),
  })
}

export function useCreerScoreur(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouveauScoreur) => creerScoreur(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleScoreurs(tournoiId) }),
  })
}

export function useModifierScoreur(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ scoreurId, entree }: { scoreurId: number; entree: NouveauScoreur }) =>
      modifierScoreur(tournoiId, scoreurId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleScoreurs(tournoiId) }),
  })
}

export function useSupprimerScoreur(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (scoreurId: number) => supprimerScoreur(tournoiId, scoreurId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleScoreurs(tournoiId) }),
  })
}

// Le PDF des cartes de scoreur (A08, 04/08/2026) : une **action** ponctuelle, comme le PDF des
// etiquettes de cible — `useMutation`, jamais `useQuery`.
export function useTelechargerCartesScoreurs(tournoiId: number) {
  return useMutation({ mutationFn: () => telechargerCartesScoreurs(tournoiId) })
}

// QR de session d'un scoreur (E16US015, ADR-0105). ⚠️ **Ce hook ne porte AUCUNE garde** : la
// mesure de sécurité — le QR n'est pas seulement caché, il n'est pas demandé — tient au **montage
// conditionnel** de `QrScoreur` dans `Scoreurs.tsx`. Une première version passait un `enabled`
// qu'aucun appelant ne mettait à `false` : un garde-fou nommé au mauvais endroit se fait contourner
// par le lecteur suivant, qui le croit actif (relevé en revue, 04/09/2026).
export function useQrScoreur(tournoiId: number, scoreurId: number, code: string) {
  return useQuery({
    // ⚠️ La clé porte le **code**, et c'est lui qui discrimine : SQLite réattribue les `id` (PK sans
    // AUTOINCREMENT), si bien que sur `['qr-scoreur', t, id]` le QR révoqué d'un supprimé se servait
    // du cache sous le nom de son successeur. `scoreurId` y figure aussi pour que la clé contienne
    // **toutes** les entrées de `queryFn` (règle React Query) — il n'ajoute aucune discrimination.
    queryKey: cleQrScoreur(tournoiId, code, scoreurId),
    queryFn: () => getQrScoreur(tournoiId, scoreurId),
  })
}
