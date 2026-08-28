// Hooks React Query du **Big Shoot Off** (E05US028) — état serveur d'une phase.
//
// ⚠️ **Les mutations vivent ici**, contrairement aux poules dont les rencontres *sont* des duels
// (ADR-0083 §7) : une volée collective n'a pas d'adversaire, donc pas de pavé à emprunter. Les deux
// mutations **écrivent directement le cache** avec l'état renvoyé — la réponse *est* la photo à
// jour, et invalider ouvrirait une fenêtre où un archer sorti paraît encore en lice. ⚠️ **Elles
// partent en direct, hors de la file hors-ligne** (`DETTE-060`) : une coupure LAN pendant une
// finale fait perdre la volée en cours.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { nouvelIdentifiant } from '../saisie/volees'

import {
  getEtatBigShootOff,
  getEtatBigShootOffSaisie,
  saisirVolee,
  validerManche,
  type EtatBigShootOff,
} from './api'

/** La clé de cache de l'état **de saisie**. Domiciliée **ici** : c'est cette feature qui l'écrit. */
export function cleBigShootOff(tournoiId: number, phaseId: number) {
  return ['big-shoot-off', tournoiId, phaseId] as const
}

/** La clé de cache de l'état **rédigé** (E05US031).
 *
 * ⚠️ **Distincte de celle de saisie, et il le faut** : une clé commune ferait écrire la photo du
 * scoreur — `prochaine_volee` comprise — dans le cache que lit l'appli publique, et le DTO
 * restreint côté serveur ne servirait plus à rien. Conséquence : les mutations écrivent **la clé
 * de saisie**, la vue publique se remettant à jour par l'invalidation globale de `useRealtime`.
 */
export function cleBigShootOffPublique(tournoiId: number, phaseId: number) {
  return ['big-shoot-off-publique', tournoiId, phaseId] as const
}

/** L'état **en consultation** — contenu restreint, lecture ouverte. Public, salle, organisation.
 *
 * ⚠️ `# DETTE-031` **élargie par E05US031** : `ServiceBigShootOff.etat` rejoue la phase entière à
 * chaque lecture, et cette lecture-ci part désormais d'une route **ouverte**, montée par l'onglet
 * public en autant d'exemplaires qu'il y a de spectateurs. Aucun `refetchInterval` : le
 * rafraîchissement vient de l'invalidation globale de `useRealtime`, donc des écritures réelles. */
export function useEtatBigShootOff(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleBigShootOffPublique(tournoiId, phaseId ?? 0),
    queryFn: () => getEtatBigShootOff(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    // Même parti que les poules et le tableau : un refus déterministe (409 phase non réglée) ne
    // gagne rien à être réessayé, et un refetch au focus écraserait une frappe en cours.
    retry: false,
    refetchOnWindowFocus: false,
  })
}

/** L'état **de saisie** — scoreur, dans son tournoi. */
export function useEtatBigShootOffSaisie(tournoiId: number, phaseId: number | null) {
  return useQuery({
    queryKey: cleBigShootOff(tournoiId, phaseId ?? 0),
    // `as number` sûr **parce que** `enabled` ci-dessous désactive la requête sur `null` — le
    // compilateur ne peut pas le voir, d'où la mention (règle 4 : un `as` se justifie).
    queryFn: () => getEtatBigShootOffSaisie(tournoiId, phaseId as number),
    enabled: phaseId !== null,
    retry: false,
    refetchOnWindowFocus: false,
  })
}

/** Saisit une volée d'un finaliste. */
export function useSaisirVolee(tournoiId: number, phaseId: number) {
  const client = useQueryClient()
  return useMutation({
    // ⚠️ **L'identifiant de saisie est engendré ici** (correctif de revue) : facultatif au DTO,
    // transmis par `api.ts`… et **jamais fourni**, si bien que `RegistreIdempotence` ne
    // dédoublonnait rien alors que l'API promettait « les mêmes garanties que la qualification »
    // (ADR-0036). Sur `/validations` ce n'était pas neutre : `Serie.valider` verrouille « le
    // prochain lot non validé » sans vérifier la manche, donc un rejeu pouvait verrouiller la
    // **suivante**. ⚠️ `nouvelIdentifiant` et non `crypto.randomUUID` : WebCrypto est réservé au
    // contexte sécurisé, et le jour J tourne en **http sur LAN**.
    mutationFn: (corps: { archerId: number; numero: number; valeurs: string[] }) =>
      saisirVolee({ tournoiId, phaseId, ...corps, identifiantSaisie: nouvelIdentifiant() }),
    onSuccess: (etat: EtatBigShootOff) =>
      client.setQueryData(cleBigShootOff(tournoiId, phaseId), etat),
  })
}

/** Valide la manche courante d'un finaliste — c'est elle qui entrera au classement. */
export function useValiderManche(tournoiId: number, phaseId: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (corps: { archerId: number }) =>
      validerManche({ tournoiId, phaseId, ...corps, identifiantSaisie: nouvelIdentifiant() }),
    onSuccess: (etat: EtatBigShootOff) =>
      client.setQueryData(cleBigShootOff(tournoiId, phaseId), etat),
  })
}
