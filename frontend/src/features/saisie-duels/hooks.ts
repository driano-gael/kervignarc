// Hooks React Query de la saisie en duels (E04US013) — état serveur du tableau et des duels, et les
// trois écritures (manche / barrage / validation) avec **file hors-ligne** et **rejeu** (E04US009).
//
// Lectures : les phases du tournoi (publiques, pour choisir un tableau), l'état d'un tableau
// reconstruit, l'état d'un duel précis. Écritures : chaque acte tente un POST ; sur **panne réseau**
// il est **mis en file** et un état **optimiste** est renvoyé (le scoreur continue) ; un **refus
// serveur** (`ErreurApi`) est une vraie erreur, propagée. Le rejeu draine la file à la reconnexion.

import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useConnexionStore } from '../../shared/stores/connexionStore'
import {
  type ActeDuelEnFile,
  cleSlot,
  useFileDuelsHorsLigneStore,
} from '../../shared/stores/fileDuelsHorsLigneStore'
import { useSessionScoreurStore } from '../../shared/stores/sessionScoreurStore'
import {
  type Duel,
  getDuel,
  getPhases,
  getTableau,
  saisirBarrage,
  saisirManche,
  type SaisirBarrage,
  type SaisirManche,
  type ValiderDuel,
  validerDuel,
} from './api'
import { injecterBarrage, injecterManche } from './duel'
import { estDejaHorsLigne, estRefusServeur } from './horsLigne'
import { rejouerActes } from './rejeu'

const clePhases = (tournoiId: number) => ['duels-phases', tournoiId] as const
const cleTableau = (tournoiId: number, phaseId: number) =>
  ['duels-tableau', tournoiId, phaseId] as const
const cleDuel = (tournoiId: number, phaseId: number, matchNumero: number) =>
  ['duels-duel', tournoiId, phaseId, matchNumero] as const

export function usePhases(tournoiId: number) {
  return useQuery({ queryKey: clePhases(tournoiId), queryFn: () => getPhases(tournoiId) })
}

export function useTableau(tournoiId: number, phaseId: number) {
  return useQuery({
    queryKey: cleTableau(tournoiId, phaseId),
    queryFn: () => getTableau(tournoiId, phaseId),
    // `retry: false` : un refus déterministe (403 hors tournoi, 409 pas un tableau) ne gagne rien à
    // être réessayé. Pas de refetch au focus : il écraserait une frappe en cours si le scoreur
    // revient sur l'onglet. Le rafraîchissement se fait sur invalidation après écriture.
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export function useDuel(tournoiId: number, phaseId: number, matchNumero: number) {
  return useQuery({
    queryKey: cleDuel(tournoiId, phaseId, matchNumero),
    queryFn: () => getDuel(tournoiId, phaseId, matchNumero),
    retry: false,
    refetchOnWindowFocus: false,
  })
}

// Un duel « placeholder » pour l'état optimiste quand le cache est vide (cas rare : on n'arrive au
// pavé qu'après avoir lu le duel). Occupants/mode inconnus : l'injection y ajoute au moins l'acte
// saisi pour que l'écran ne reste pas figé, la vérité revenant au rejeu.
function placeholderDuel(matchNumero: number): Duel {
  return {
    numero: matchNumero,
    tour: 0,
    place_en_jeu: null,
    haut: null,
    bas: null,
    est_bye: false,
    mode: null,
    nb_manches: null,
    nb_fleches_par_volee: null,
    points_pour_gagner: null,
    zones: [],
    validee_par: null,
    manches: [],
    barrage: null,
    resultat: null,
  }
}

// Fabrique une mutation d'acte de duel : chemin nominal (POST direct, l'accusé rafraîchit le cache),
// repli **hors-ligne** (mise en file + état optimiste), et — au succès **en ligne** — invalidation +
// supersession de la file + drainage. `optimiste` construit l'état local à afficher hors-ligne.
function useMutationActe<C extends { identifiant_saisie: string }>(
  tournoiId: number,
  phaseId: number,
  matchNumero: number,
  envoyer: (corps: C) => Promise<Duel>,
  versActe: (corps: C) => ActeDuelEnFile,
  optimiste: (base: Duel, corps: C) => Duel,
) {
  const queryClient = useQueryClient()
  const mettreEnFile = useFileDuelsHorsLigneStore((state) => state.mettreEnFile)
  return useMutation<Duel, Error, C>({
    mutationFn: async (corps) => {
      const enFile = () => {
        mettreEnFile(versActe(corps))
        const base =
          queryClient.getQueryData<Duel>(cleDuel(tournoiId, phaseId, matchNumero)) ??
          placeholderDuel(matchNumero)
        return optimiste(base, corps)
      }
      // Lien déjà tombé : on met en file sans tenter le POST (qui pendrait jusqu'à expiration).
      if (estDejaHorsLigne(useConnexionStore.getState().statut)) return enFile()
      try {
        return await envoyer(corps)
      } catch (erreur) {
        if (estRefusServeur(erreur)) throw erreur // le serveur a refusé → vraie erreur
        return enFile() // panne réseau → mise en file
      }
    },
    onSuccess: (duel, corps) => {
      queryClient.setQueryData(cleDuel(tournoiId, phaseId, matchNumero), duel)
      const enFile = useFileDuelsHorsLigneStore
        .getState()
        .enAttente.some((a) => a.identifiant_saisie === corps.identifiant_saisie)
      // Hors-ligne (optimiste mis en file) : **ne pas invalider** — une relecture échouerait et
      // ferait retomber l'écran en erreur ; la vérité serveur reviendra au rejeu.
      if (enFile) return
      // Succès **en ligne** : le duel fait autorité. On invalide le duel et le tableau (une manche
      // change le résultat ; une validation fait **avancer** le tableau), on supersède une éventuelle
      // attente hors-ligne du **même** emplacement (une valeur neuve en ligne ne doit pas être
      // réécrasée par un vieux rejeu), et — le réseau étant revenu — on **draine** le reste.
      void queryClient.invalidateQueries({ queryKey: cleDuel(tournoiId, phaseId, matchNumero) })
      void queryClient.invalidateQueries({ queryKey: cleTableau(tournoiId, phaseId) })
      useFileDuelsHorsLigneStore.getState().retirerSlot(cleSlot(versActe(corps)))
      void draineLaFileDuels(queryClient)
    },
  })
}

export function useSaisirManche(tournoiId: number, phaseId: number, matchNumero: number) {
  return useMutationActe<SaisirManche>(
    tournoiId,
    phaseId,
    matchNumero,
    saisirManche,
    (corps) => ({ type: 'manche', ...corps }),
    injecterManche,
  )
}

export function useSaisirBarrage(tournoiId: number, phaseId: number, matchNumero: number) {
  return useMutationActe<SaisirBarrage>(
    tournoiId,
    phaseId,
    matchNumero,
    saisirBarrage,
    (corps) => ({ type: 'barrage', ...corps }),
    injecterBarrage,
  )
}

export function useValiderDuel(tournoiId: number, phaseId: number, matchNumero: number) {
  return useMutationActe<ValiderDuel>(
    tournoiId,
    phaseId,
    matchNumero,
    validerDuel,
    (corps) => ({ type: 'validation', ...corps }),
    // Hors-ligne, la validation **verrouille l'écran localement** (`validation_en_attente`) — comme le
    // ferait le serveur en ligne (`DuelVerrouille`). Sinon le scoreur pourrait rééditer une manche
    // APRÈS avoir validé : au rejeu FIFO la validation scellerait le résultat d'avant correction, et la
    // manche corrigée rebondirait en 422 (perte silencieuse, revue adversariale). Réconcilié au rejeu.
    (base) => ({ ...base, en_attente: true, validation_en_attente: true }),
  )
}

// Rejoue un acte de la file en le routant vers son endpoint (le champ `type` discrimine).
function envoyerActe(acte: ActeDuelEnFile): Promise<Duel> {
  if (acte.type === 'manche') {
    return saisirManche({
      tournoi_id: acte.tournoi_id,
      phase_id: acte.phase_id,
      match_numero: acte.match_numero,
      numero: acte.numero,
      valeurs_haut: acte.valeurs_haut,
      valeurs_bas: acte.valeurs_bas,
      identifiant_saisie: acte.identifiant_saisie,
    })
  }
  if (acte.type === 'barrage') {
    return saisirBarrage({
      tournoi_id: acte.tournoi_id,
      phase_id: acte.phase_id,
      match_numero: acte.match_numero,
      fleche_haut: acte.fleche_haut,
      fleche_bas: acte.fleche_bas,
      gagnant_designe: acte.gagnant_designe,
      identifiant_saisie: acte.identifiant_saisie,
    })
  }
  return validerDuel({
    tournoi_id: acte.tournoi_id,
    phase_id: acte.phase_id,
    match_numero: acte.match_numero,
    identifiant_saisie: acte.identifiant_saisie,
  })
}

// Draine la file hors-ligne des duels : rejoue les actes en attente, dans l'ordre, retire les traités
// et invalide les duels/tableaux touchés (vérité serveur). Idempotent et **ré-entrance protégée** par
// le drapeau `synchronisation`. Fonction module (pas un hook) : appelée par le hook de rejeu **et**
// par un succès de saisie en ligne.
async function draineLaFileDuels(queryClient: QueryClient): Promise<void> {
  const store = useFileDuelsHorsLigneStore.getState()
  if (store.enAttente.length === 0 || store.synchronisation) return
  store.demarrerSync()
  try {
    const estEncoreEnFile = (acte: ActeDuelEnFile) =>
      useFileDuelsHorsLigneStore
        .getState()
        .enAttente.some((a) => a.identifiant_saisie === acte.identifiant_saisie)
    const { traites, refuses } = await rejouerActes(store.enAttente, envoyerActe, estEncoreEnFile)
    const { confirmer } = useFileDuelsHorsLigneStore.getState()
    const tableaux = new Set<string>()
    for (const acte of traites) {
      confirmer(acte.identifiant_saisie)
      void queryClient.invalidateQueries({
        queryKey: cleDuel(acte.tournoi_id, acte.phase_id, acte.match_numero),
      })
      tableaux.add(`${acte.tournoi_id}:${acte.phase_id}`)
    }
    for (const [, cle] of tableaux.entries()) {
      const [t, p] = cle.split(':').map(Number)
      void queryClient.invalidateQueries({ queryKey: cleTableau(t ?? 0, p ?? 0) })
    }
    for (const acte of refuses) {
      // Refus **définitif** au rejeu (4xx métier). Perte visible (la relecture retire l'optimiste),
      // journalisée. Cas assumé, ADR-0037. Les transitoires (401/409/5xx…) ne passent pas ici.
      console.error('Acte de duel refusé définitivement au rejeu, retiré de la file', acte)
    }
  } finally {
    useFileDuelsHorsLigneStore.getState().terminerSync()
  }
}

// Rejeu de la file hors-ligne des duels. Monté sur l'écran de saisie du scoreur. Draine la file **par
// transition** — reconnexion WebSocket, ou retour du **jeton scoreur** (re-connexion après un 401) —
// jamais sur la longueur de file (boucle chaude). On ne draine pas sans jeton : les endpoints de duel
// sont scopés « scoreur » (un POST sans jeton referait un 401 inutile). (Le 3ᵉ filet — succès d'une
// saisie en ligne — vit dans `onSuccess`.)
export function useRejeuDuelsHorsLigne(): void {
  const queryClient = useQueryClient()
  const statut = useConnexionStore((state) => state.statut)
  const jeton = useSessionScoreurStore((state) => state.jeton)

  useEffect(() => {
    if (statut !== 'connecte' || jeton === null) return
    void draineLaFileDuels(queryClient)
  }, [statut, jeton, queryClient])
}

// Nombre d'actes de duel en attente d'envoi (pour l'annotation « en attente » de l'écran).
export function useDuelsEnAttente(): number {
  return useFileDuelsHorsLigneStore((state) => state.enAttente.length)
}
