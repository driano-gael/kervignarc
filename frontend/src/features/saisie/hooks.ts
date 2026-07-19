// Hooks React Query de la saisie (E04US002) — état serveur de la grille, des séries et du contexte.
//
// Lectures : la grille du poste (dépend du **départ courant** en session serveur — un 409 tant qu'il
// n'est pas fixé, cf. `Saisie.tsx`), la série de chaque archer, le barème et le grain de la phase, la
// liste des départs. Écritures : fixer le départ courant, saisir une volée. Chaque écriture invalide
// ce qu'elle change (changer de départ change les archers ; saisir change la série de l'archer).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { useConnexionStore } from '../../shared/stores/connexionStore'
import { useFileHorsLigneStore } from '../../shared/stores/fileHorsLigneStore'
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
    // lieu de rester bloqué. Un refus **serveur** (`ErreurApi` : hors-cible, blason introuvable…) est
    // au contraire une vraie erreur, propagée : on ne met pas en file ce que le serveur a refusé.
    mutationFn: async (corps) => {
      try {
        return await saisirVolee(corps)
      } catch (erreur) {
        if (erreur instanceof ErreurApi) throw erreur
        mettreEnFile(corps)
        return serieOptimiste(queryClient.getQueryData<Serie>(cleSerie(tournoiId, archerId)), corps)
      }
    },
    // On pose la série (réelle ou optimiste) dans le cache. On **n'invalide que si la saisie a
    // atteint le serveur** : hors-ligne, un `invalidateQueries` déclencherait une relecture qui
    // échoue et ferait retomber la série en erreur (grille bloquée) — la vérité serveur reviendra à
    // la reconnexion, quand le rejeu invalidera lui-même la série.
    onSuccess: (serie, corps) => {
      queryClient.setQueryData(cleSerie(tournoiId, archerId), serie)
      const enFile = useFileHorsLigneStore
        .getState()
        .enAttente.some((c) => c.identifiant_saisie === corps.identifiant_saisie)
      if (!enFile) void queryClient.invalidateQueries({ queryKey: cleSerie(tournoiId, archerId) })
    },
  })
}

// Rejeu de la file hors-ligne à la reconnexion (E04US009, ADR-0037). Monté sur l'écran de saisie du
// poste. Se déclenche quand le lien WebSocket **revient** (`connecte`) : sur un LAN, la restauration
// du réseau coïncide avec la réouverture du WebSocket (reconnexion auto ~1 s). Il renvoie la file
// dans l'ordre, retire les saisies traitées et **relit** les séries concernées (vérité serveur).
export function useRejeuFileHorsLigne(): void {
  const queryClient = useQueryClient()
  const statut = useConnexionStore((state) => state.statut)

  useEffect(() => {
    if (statut !== 'connecte') return
    const store = useFileHorsLigneStore.getState()
    if (store.enAttente.length === 0 || store.synchronisation) return

    store.demarrerSync()
    void (async () => {
      try {
        const { traitees, refusees } = await rejouer(store.enAttente, (corps) => saisirVolee(corps))
        const { confirmer } = useFileHorsLigneStore.getState()
        for (const corps of traitees) {
          confirmer(corps.identifiant_saisie)
          void queryClient.invalidateQueries({
            queryKey: cleSerie(corps.tournoi_id, corps.archer_id),
          })
        }
        for (const corps of refusees) {
          // Perte **visible** (la relecture ci-dessus retire la volée optimiste de la grille) : on la
          // journalise côté client. Cas assumé, cf. ADR-0037.
          console.error('Saisie hors-ligne refusée au rejeu, retirée de la file', corps)
        }
      } finally {
        useFileHorsLigneStore.getState().terminerSync()
      }
    })()
    // Dépend du seul `statut` : le déclencheur est la **reconnexion**. Ne pas ajouter la longueur de
    // file en dépendance (un rejeu interrompu par une panne rouvrirait aussitôt une boucle chaude tant
    // que le lien semble « connecté ») — la prochaine transition de lien relancera le rejeu.
  }, [statut, queryClient])
}
