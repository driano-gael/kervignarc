// Hooks React Query de la feature « competition » (E00US011).
//
// Le classement est l'état **serveur** (lecture) ; les autres cas d'usage sont des
// **mutations**. Après chaque écriture, le backend diffuse un événement WebSocket qui, via
// `useRealtime`, invalide le cache — le classement se met donc à jour **en direct** sur tous
// les clients. On invalide aussi côté mutation (onSuccess) pour un rafraîchissement immédiat
// même si le lien temps réel est momentanément coupé.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ajouterArcher,
  annoncerBarrage,
  annulerBarrage,
  cloreBarrage,
  creerTournoi,
  getBarrages,
  getClassement,
  getTournois,
  type ModifierTournoi,
  modifierTournoi,
  type NouvelArcher,
  placerArcher,
  saisirMancheBarrage,
  supprimerTournoi,
  type TirBarrage,
} from './api'

// Exportée : la feature `archers` (E02US003) invalide le classement après une édition ou une
// désinscription — un archer corrigé ou retiré doit quitter le tableau sans attendre. La clé se
// déclare **une fois**, ici, où vit la requête ; deux littéraux `['classement', id]` finiraient
// par diverger et l'invalidation raterait sa cible en silence. Elle **préfixe** la clé filtrée par
// catégorie (E06US001) : invalider `['classement', id]` couvre toutes les vues filtrées du tournoi.
export const cleClassement = (tournoiId: number, categorieId?: number) =>
  categorieId === undefined
    ? (['classement', tournoiId] as const)
    : (['classement', tournoiId, categorieId] as const)
// Exportée : la feature « accueil » (E14US001) invalide la liste des tournois après une transition
// de cycle de vie (le statut change → badge, frise, accueil contextualisé). La clé se déclare **une
// fois**, ici où vit la requête, pour ne pas diverger d'un littéral `['tournois']` recopié ailleurs.
export const CLE_TOURNOIS = ['tournois'] as const

// `categorieId` optionnel : filtre le classement à une catégorie (les rangs restent globaux).
export function useClassement(tournoiId: number, categorieId?: number) {
  return useQuery({
    queryKey: cleClassement(tournoiId, categorieId),
    queryFn: () => getClassement(tournoiId, categorieId),
  })
}

export function useTournois() {
  return useQuery({ queryKey: CLE_TOURNOIS, queryFn: getTournois })
}

export function useCreerTournoi() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: creerTournoi,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS }),
  })
}

// Édition et cycle de vie (E01US002). Chaque mutation invalide la liste des tournois : la
// vue se resynchronise (statut, métadonnées, disparition d'un tournoi supprimé).
export function useModifierTournoi() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, entree }: { id: number; entree: ModifierTournoi }) =>
      modifierTournoi(id, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS }),
  })
}

// Le démarrer/terminer isolés (E01US002) ont laissé place au **pilotage générique** du cycle de vie
// par la frise de l'accueil (E14US001, `useTransitionnerTournoi`), qui couvre les 7 statuts d'un
// seul geste. `terminer` garde sa voie dédiée côté complétude (message chiffré d'avertissement).

export function useSupprimerTournoi() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => supprimerTournoi(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_TOURNOIS }),
  })
}

export function useAjouterArcher(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouvelArcher) => ajouterArcher(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}

export function usePlacerArcher(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ archerId, cible }: { archerId: number; cible: number }) =>
      placerArcher(archerId, cible),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) }),
  })
}

// --- barrage de places décisives (E06US003, ADR-0066) ---

// Clé exportée pour la même raison que `cleClassement` : elle est invalidée depuis plusieurs
// mutations, et deux littéraux recopiés finiraient par diverger en silence.
export const cleBarrages = (tournoiId: number) => ['barrages', tournoiId] as const

export function useBarrages(tournoiId: number) {
  return useQuery({ queryKey: cleBarrages(tournoiId), queryFn: () => getBarrages(tournoiId) })
}

// ⚠️ Chaque mutation invalide **le classement autant que les barrages** : un barrage tiré change
// les rangs publiés (les ex æquo deviennent consécutifs) et fait disparaître l'égalité de la liste
// à départager. N'invalider que `cleBarrages` laisserait le tableau afficher un rang partagé que
// l'archer vient de perdre au tir — l'écart le plus visible du jour J.
function useMutationBarrage<T>(tournoiId: number, action: (variables: T) => Promise<unknown>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: action,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cleBarrages(tournoiId) })
      void queryClient.invalidateQueries({ queryKey: cleClassement(tournoiId) })
    },
  })
}

export function useAnnoncerBarrage(tournoiId: number) {
  return useMutationBarrage(tournoiId, (rang: number) => annoncerBarrage(tournoiId, rang))
}

export function useSaisirMancheBarrage(tournoiId: number) {
  return useMutationBarrage(
    tournoiId,
    ({ barrageId, tirs, manche }: { barrageId: number; tirs: TirBarrage[]; manche?: number }) =>
      saisirMancheBarrage(tournoiId, barrageId, tirs, manche),
  )
}

export function useCloreBarrage(tournoiId: number) {
  return useMutationBarrage(tournoiId, (barrageId: number) => cloreBarrage(tournoiId, barrageId))
}

// Annulation d'un barrage annoncé par erreur. Sans elle, un barrage qu'on ne veut pas faire tirer
// restait affiché indéfiniment et son rang bloquait toute nouvelle annonce (`clore` exige un
// barrage résolu).
export function useAnnulerBarrage(tournoiId: number) {
  return useMutationBarrage(tournoiId, (barrageId: number) => annulerBarrage(tournoiId, barrageId))
}
