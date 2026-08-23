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
  type AnnonceBarrage,
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
// par diverger et l'invalidation raterait sa cible en silence.
//
// ⚠️ **La clé reste ancrée au tournoi alors que la donnée est celle d'un départ** (ADR-0075), et
// c'est délibéré : React Query invalide **par préfixe**, donc `['classement', tournoiId]` couvre
// les N créneaux du tournoi *et* leurs vues filtrées par catégorie. Les six invalidations
// existantes (archers, forfaits, barrages, phases) raisonnent au tournoi — un archer corrigé peut
// tirer dans n'importe quel créneau. Descendre la clé au seul départ les aurait toutes fait rater
// leur cible **en silence** : l'écran cesserait de se rafraîchir sans qu'aucune erreur ne le dise.
export const cleClassement = (tournoiId: number) => ['classement', tournoiId] as const

// La clé d'une vue **précise** : ce créneau, éventuellement cette catégorie. Préfixée par la
// précédente, donc couverte par ses invalidations.
export const cleClassementDepart = (tournoiId: number, departId: number, categorieId?: number) =>
  categorieId === undefined
    ? (['classement', tournoiId, departId] as const)
    : (['classement', tournoiId, departId, categorieId] as const)
// Exportée : la feature « accueil » (E14US001) invalide la liste des tournois après une transition
// de cycle de vie (le statut change → badge, frise, accueil contextualisé). La clé se déclare **une
// fois**, ici où vit la requête, pour ne pas diverger d'un littéral `['tournois']` recopié ailleurs.
export const CLE_TOURNOIS = ['tournois'] as const

// Le pas de rafraîchissement de cette lecture. Chaque feature déclare le sien — 5 s ici comme pour
// la complétude, les jalons et la supervision ; 10 s pour le suivi du déroulé, davantage ailleurs :
// il n'y a pas de parité générale à revendiquer, seulement une constante nommée par module.
const INTERVALLE_POLL_MS = 5000

// Le classement **d'un créneau** (ADR-0075). `categorieId` optionnel : filtre l'affichage à une
// catégorie (les rangs restent ceux du classement complet du départ).
//
// `departId` peut être `null` le temps que la liste des créneaux arrive : la requête est alors
// **désactivée** plutôt que lancée sur un identifiant inventé. Un `enabled: false` rend un état
// `pending`, que l'appelant affiche comme un chargement — ce qu'il est réellement.
export function useClassement(tournoiId: number, departId: number | null, categorieId?: number) {
  return useQuery({
    queryKey: cleClassementDepart(tournoiId, departId ?? 0, categorieId),
    queryFn: () => getClassement(departId as number, categorieId),
    enabled: departId !== null,
  })
}

// `live` — **pollé sur demande, jamais par défaut**. Le `statut` qui sort d'ici pilote des écrans
// entiers de l'administration : depuis E16US012, « Prêt à terminer ? » y prend son verdict, sa
// raison **et** la présence de son bouton. Sans rafraîchissement (le `staleTime` global est de 30 s,
// `refetchOnWindowFocus` est désactivé, et aucune transition de cycle de vie ne diffuse d'événement
// WebSocket), un second poste restait sur un statut périmé indéfiniment : le PC reprend le tournoi,
// la tablette continue de croire à la pause et **fait disparaître le bouton « Terminer »**. L'appli
// empêchait alors sans rien dire — l'inverse de `D-15`/`P-3`, sans même un 409 pour détromper
// l'organisateur (5ᵉ passe de revue, axe D).
//
// ⚠️ **Pourquoi une option et non un poll inconditionnel.** La 5ᵉ passe l'avait armé pour tout le
// monde, sur un inventaire faux — « deux consommateurs, tous deux des écrans d'administration ».
// Ils sont **trois**, et le troisième est la **porte publique** : `GestionTournois` est monté sans
// condition par `public/AccueilPublic`. Chaque téléphone de spectateur aurait donc interrogé
// `GET /api/v1/tournois` toutes les 5 s, jour J, sur le LAN — contre la doctrine que le dépôt écrit
// noir sur blanc pour les routes ouvertes (`big-shoot-off/hooks.ts` : « aucun `refetchInterval` :
// le rafraîchissement vient de l'invalidation globale de `useRealtime` »). Relevé en 6ᵉ passe par
// deux axes. Seule la coquille admin demande donc le direct ; le public garde le comportement
// d'avant.
export function useTournois({ live = false }: { live?: boolean } = {}) {
  return useQuery({
    queryKey: CLE_TOURNOIS,
    queryFn: getTournois,
    ...(live ? { refetchInterval: INTERVALLE_POLL_MS, staleTime: 0 } : {}),
  })
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
// ⚠️ Clé **au tournoi**, volontairement, alors que le barrage pend au départ (ADR-0075) : la route
// `GET /tournois/{id}/barrages` rend tous les créneaux en une fois, et la lui indexer par départ
// mettrait N copies de la même charge en cache. Le tri par créneau est donc à l'affichage
// (`PanneauBarrages`), pas au cache — la seule chose à ne jamais oublier est de le **faire**.
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
  return useMutationBarrage(tournoiId, (annonce: AnnonceBarrage) =>
    annoncerBarrage(tournoiId, annonce),
  )
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
