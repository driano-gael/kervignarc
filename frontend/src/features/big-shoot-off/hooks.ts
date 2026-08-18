// Hooks React Query du **Big Shoot Off** (E05US028) — état serveur d'une phase.
//
// ⚠️ **Les mutations vivent ici**, contrairement aux poules — dont les rencontres s'écrivent par
// `features/saisie-duels` parce qu'elles *sont* des duels (ADR-0083 §7). Une volée collective n'a
// pas d'adversaire, donc pas de pavé de duel à emprunter.
//
// Les deux mutations **écrivent directement le cache** avec l'état renvoyé, au lieu d'invalider :
// la réponse *est* la photo complète et à jour, donc un aller-retour de plus ne ferait qu'ouvrir
// une fenêtre où l'écran montre un archer sorti comme encore en lice.
//
// ⚠️ **Ces deux mutations partent en direct, hors de la file hors-ligne d'E04US009**
// (`DETTE-060`) : une coupure LAN pendant une finale fait perdre la volée en cours. Le marqueur
// était annoncé par le registre sur ce fichier sans y figurer — corrigé à la revue d'E05US028, une
// dette dont le point d'accroche est introuvable n'est pas tracée.

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
 * ⚠️ **Distincte de celle de saisie, et il le faut** : les deux routes rendent deux formes du même
 * objet. Une clé commune ferait écrire la photo du scoreur — `prochaine_volee` comprise — dans le
 * cache que lit l'appli publique ; le DTO restreint côté serveur ne servirait alors plus à rien,
 * le front l'ayant contourné tout seul.
 *
 * Conséquence à connaître : les deux mutations ci-dessous écrivent **la clé de saisie**, pas
 * celle-ci. La vue publique se remet à jour par l'invalidation globale de `useRealtime`, qui part de
 * toute écriture serveur — même chemin que les poules et le tableau, et non un cas particulier. */
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
    // ⚠️ **L'identifiant de saisie est engendré ici** (correctif de revue E05US028). Il était
    // facultatif au DTO, transmis par `api.ts`… et **jamais fourni** : `_cle_idempotence` rendait
    // donc toujours `null` et `RegistreIdempotence` ne dédoublonnait rien, alors que la note de
    // module de l'API promettait « les mêmes garanties que la saisie de qualification » (ADR-0036).
    // Les deux autres surfaces de saisie le déclarent obligatoire ; le Big Shoot Off était la seule
    // sans. Sur `/validations` ce n'était pas neutre : `Serie.valider` verrouille « le prochain lot
    // de N volées non validées » sans vérifier qu'il s'agit de la manche courante, donc un rejeu
    // pouvait verrouiller les volées de la manche **suivante**.
    //
    // ⚠️ `nouvelIdentifiant` et non `crypto.randomUUID` : WebCrypto n'expose `randomUUID` qu'en
    // contexte sécurisé, et le jour J tourne en **http sur LAN**. Le repli `getRandomValues` est
    // déjà écrit là-bas, on le réutilise plutôt que de le redécouvrir en salle.
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
