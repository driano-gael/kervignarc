// Hooks React Query de la saisie (E04US002) — état serveur de la grille, des séries et du contexte.
//
// Lectures : la grille du poste (dépend du **départ courant** en session serveur — un 409 tant qu'il
// n'est pas fixé, cf. `Saisie.tsx`), la série de chaque archer, le barème et le grain de la phase, la
// liste des départs. Écritures : fixer le départ courant, saisir une volée. Chaque écriture invalide
// ce qu'elle change (changer de départ change les archers ; saisir change la série de l'archer).

import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useConnexionStore } from '../../shared/stores/connexionStore'
import { useFileHorsLigneStore, type VoleeEnFile } from '../../shared/stores/fileHorsLigneStore'
import { useSessionPosteStore } from '../../shared/stores/sessionPosteStore'
import {
  fixerDepartCourant,
  getBareme,
  getDepartsDuPoste,
  getGrain,
  getGrille,
  getSerie,
  saisirVolee,
  type SaisirVolee,
  type Serie,
} from './api'
import { estDejaHorsLigne, estRefusServeur } from './horsLigne'
import { rejouer } from './rejeu'
import { serieOptimiste } from './volees'

const cleGrille = () => ['saisie-grille'] as const
const cleSerie = (tournoiId: number, archerId: number) =>
  ['saisie-serie', tournoiId, archerId] as const
const cleBareme = (tournoiId: number) => ['saisie-bareme', tournoiId] as const
const cleGrain = (tournoiId: number) => ['saisie-grain', tournoiId] as const
const cleDeparts = (tournoiId: number) => ['saisie-departs', tournoiId] as const

export function useGrille() {
  // Pas de `retry` : un 409 « départ courant non défini » est un état **attendu** (pas un incident
  // réseau) que `Saisie.tsx` inspecte pour afficher le sélecteur de départ — inutile de réessayer.
  return useQuery({ queryKey: cleGrille(), queryFn: getGrille, retry: false })
}

export function useSerie(tournoiId: number, archerId: number) {
  return useQuery({
    queryKey: cleSerie(tournoiId, archerId),
    queryFn: () => getSerie(tournoiId, archerId),
    // `retry: false` : un 403 (hors cible) est déterministe, inutile de réessayer. Pas de refetch au
    // focus fenêtre : il écraserait un tampon en cours de frappe si un autre acteur touchait la même
    // série (co-saisie). Le rafraîchissement se fait sur invalidation après la propre écriture du poste.
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export function useBareme(tournoiId: number) {
  return useQuery({
    queryKey: cleBareme(tournoiId),
    queryFn: () => getBareme(tournoiId),
    retry: false,
  })
}

export function useGrain(tournoiId: number) {
  return useQuery({
    queryKey: cleGrain(tournoiId),
    queryFn: () => getGrain(tournoiId),
    retry: false,
  })
}

export function useDeparts(tournoiId: number) {
  return useQuery({ queryKey: cleDeparts(tournoiId), queryFn: () => getDepartsDuPoste(tournoiId) })
}

export function useFixerDepart() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (departId: number) => fixerDepartCourant(departId),
    // Changer de départ change les archers servis **et** leurs séries : on invalide la grille et
    // toutes les séries en cache (préfixe `saisie-serie`) pour repartir de zéro sur le bon départ.
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cleGrille() })
      void queryClient.invalidateQueries({ queryKey: ['saisie-serie'] })
    },
  })
}

export function useSaisirVolee(tournoiId: number, archerId: number) {
  const queryClient = useQueryClient()
  const mettreEnFile = useFileHorsLigneStore((state) => state.mettreEnFile)
  return useMutation<Serie, Error, SaisirVolee>({
    // Chemin nominal : POST direct, l'accusé (la série renvoyée) rafraîchit le cache. En cas de
    // **panne réseau** (le `fetch` rejette, pas une `ErreurApi` : le serveur n'a pas répondu), on met
    // la saisie **en file** (E04US009) et on renvoie une série **optimiste** — le marqueur avance au
    // lieu de rester bloqué. Un refus **serveur** (`ErreurApi`) est au contraire une vraie erreur,
    // propagée : on ne met pas en file ce que le serveur a refusé ici et maintenant.
    mutationFn: async (corps) => {
      const enFile = () => {
        mettreEnFile(corps)
        return serieOptimiste(queryClient.getQueryData<Serie>(cleSerie(tournoiId, archerId)), corps)
      }
      // Court-circuit : si le lien WebSocket est **déjà** tombé, on se sait hors-ligne — on met en
      // file **sans tenter** le POST, qui pendrait sinon jusqu'à son délai d'expiration (pas de
      // timeout sur `fetch`) et bloquerait le bouton « Enregistrement… » de longues secondes.
      if (estDejaHorsLigne(useConnexionStore.getState().statut)) return enFile()
      try {
        return await saisirVolee(corps)
      } catch (erreur) {
        if (estRefusServeur(erreur)) throw erreur // le serveur a répondu un refus → vraie erreur
        return enFile() // panne réseau (fetch rejette, lien encore cru connecté) → mise en file
      }
    },
    onSuccess: (serie, corps) => {
      queryClient.setQueryData(cleSerie(tournoiId, archerId), serie)
      const enFile = useFileHorsLigneStore
        .getState()
        .enAttente.some((c) => c.identifiant_saisie === corps.identifiant_saisie)
      // Hors-ligne (série optimiste mise en file) : **ne pas invalider** — une relecture échouerait et
      // ferait retomber la grille en erreur ; la vérité serveur reviendra au rejeu.
      if (enFile) return
      // Succès **en ligne** : la série fait autorité. On invalide pour réconcilier le « quand », on
      // supersède une éventuelle attente hors-ligne du même emplacement (une valeur neuve saisie en
      // ligne ne doit pas être réécrasée par un vieux rejeu), et — le réseau étant clairement revenu —
      // on **draine** le reste du backlog (filet pour une saisie enfilée alors que le WS n'était pas
      // tombé — sans quoi elle attendrait une transition WS, cf. ADR-0037).
      void queryClient.invalidateQueries({ queryKey: cleSerie(tournoiId, archerId) })
      useFileHorsLigneStore.getState().retirerVolee(corps.tournoi_id, corps.archer_id, corps.numero)
      void draineLaFile(queryClient)
    },
  })
}

// Draine la file hors-ligne : renvoie les saisies en attente, dans l'ordre, retire les traitées et
// relit leurs séries (vérité serveur). Idempotent et **ré-entrance protégée** par le drapeau
// `synchronisation` (les deux `getState()` → check → `demarrerSync()` sont synchrones, pas de course).
// Fonction module (pas un hook) : appelée par le hook de rejeu **et** par un succès de saisie en ligne.
async function draineLaFile(queryClient: QueryClient): Promise<void> {
  const store = useFileHorsLigneStore.getState()
  if (store.enAttente.length === 0 || store.synchronisation) return
  store.demarrerSync()
  try {
    // `store.enAttente` est un instantané ; `estEncoreEnFile` relit l'état **vivant** avant chaque
    // envoi, pour sauter une volée qu'une saisie en ligne concurrente (`retirerVolee`) a superseded.
    const estEncoreEnFile = (corps: VoleeEnFile) =>
      useFileHorsLigneStore
        .getState()
        .enAttente.some((c) => c.identifiant_saisie === corps.identifiant_saisie)
    const { traitees, refusees } = await rejouer(
      store.enAttente,
      (corps) => saisirVolee(corps),
      estEncoreEnFile,
    )
    const { confirmer } = useFileHorsLigneStore.getState()
    for (const corps of traitees) {
      confirmer(corps.identifiant_saisie)
      void queryClient.invalidateQueries({ queryKey: cleSerie(corps.tournoi_id, corps.archer_id) })
    }
    for (const corps of refusees) {
      // Refus **définitif** au rejeu (4xx métier). Perte visible (la relecture retire la volée
      // optimiste de la grille), journalisée. Cas assumé, cf. ADR-0037. Les transitoires (401/5xx…)
      // NE passent pas ici : `rejouer` les garde en file et s'arrête (`interrompu`).
      console.error('Saisie hors-ligne refusée définitivement au rejeu, retirée de la file', corps)
    }
  } finally {
    useFileHorsLigneStore.getState().terminerSync()
  }
}

// Rejeu de la file hors-ligne (E04US009, ADR-0037). Monté sur l'écran de saisie du poste. Draine la
// file sur deux déclencheurs, chacun **par transition** (pas de boucle chaude) :
//  - le lien WebSocket **revient** (`connecte`) : sur un LAN, la restauration du réseau coïncide avec
//    la réouverture du WebSocket (reconnexion auto ~1 s) — le cas nominal.
//  - le **jeton de poste revient** (re-rattachement) : après un rejeu qui a buté sur un 401 (serveur
//    redémarré → session purgée), le WebSocket reste connecté ; c'est le re-rattachement, pas une
//    transition de lien, qui doit relancer le rejeu des saisies gardées en file.
// (Un troisième filet — succès d'une saisie en ligne — vit dans `useSaisirVolee.onSuccess`.)
// On ne draine pas sans jeton : les endpoints de saisie sont scopés « poste » (un POST sans jeton
// referait un 401 inutile).
export function useRejeuFileHorsLigne(): void {
  const queryClient = useQueryClient()
  const statut = useConnexionStore((state) => state.statut)
  const jeton = useSessionPosteStore((state) => state.jeton)

  useEffect(() => {
    if (statut !== 'connecte' || jeton === null) return
    void draineLaFile(queryClient)
    // Dépend de `statut` et `jeton` (transitions), pas de la longueur de file : un rejeu interrompu
    // par une panne ne doit pas rouvrir une boucle chaude tant que le lien semble « connecté ». La
    // prochaine transition (lien ou jeton), ou un succès de saisie en ligne, relancera le drainage.
  }, [statut, jeton, queryClient])
}
