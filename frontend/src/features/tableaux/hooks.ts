// Hooks React Query de la vue publique des tableaux (E07US005).
//
// **Live** au sens du CA : le rafraîchissement principal est le canal temps réel — toute écriture
// serveur publie un `donnees_modifiees` post-commit que `useRealtime` traduit en invalidation
// globale, donc l'arbre se remet à jour tout seul dès qu'un scoreur valide un duel. Le poll n'est
// qu'un **filet** (WebSocket tombé, événement manqué), d'où un intervalle long.
//
// ⚠️ `# DETTE-031`, que cette US **élargit**. Chaque appel reconstruit intégralement chaque tableau
// du tournoi côté serveur (classement complet, arbre rebâti, duels rejoués), sans cache ni plafond,
// sur une route publique non authentifiée. Deux aggravations propres à cette US :
//  - la reconstruction est payée **une fois par phase en tableau**, pas une fois par appel ;
//  - la surface est en **autant d'exemplaires qu'il y a de spectateurs** — même régime que la carte
//    de suivi d'E07US008, et le cache React Query étant par navigateur, rien ne se mutualise.
// ⚠️ **Ce qui limite la casse est le montage conditionnel du composant, pas un drapeau.** Un
// premier jet portait un paramètre `actif` qu'aucun appelant ne passait — et trois textes, dont le
// registre de dette, lui attribuaient la protection : un futur mainteneur y aurait cru. Le vrai
// mécanisme est celui qu'`EcranSalle` a appliqué à `useSuiviDeroule` : la vue n'est **rendue** que
// lorsqu'elle est affichée (`if (vue === 'tableaux')` côté salle, ternaire d'onglets côté public),
// donc React Query démonte l'observateur et arrête l'intervalle. `useSuiviDeroule` n'a pas non plus
// de paramètre `actif` — la convention est cohérente, il ne fallait pas s'en écarter.
//
// ⚠️ **Cette protection ne borne plus l'endpoint depuis E16US004** (élargissement inscrit au
// registre, cf. DETTE-031). L'onglet public « Suivi » monte désormais `useTableauxDesDeparts`, et
// c'est l'onglet d'**atterrissage par défaut** dès qu'on suit un archer (D-09) : le poll ne se paie
// donc plus seulement quand on ouvre « Tableaux », mais dès l'ouverture de l'appli, sur chaque
// téléphone de la salle. Ce qui borne encore le coût côté suivi est la **liste de départs**
// transmise (les seuls créneaux où les archers suivis tirent) et le fait qu'aucun poll ne parte
// sans suivi — pas le montage.

import { useQueries, useQuery } from '@tanstack/react-query'
import { getTableaux } from './api'

const INTERVALLE_POLL_MS = 20000

const cleTableaux = (departId: number | null) => ['tableaux', departId] as const

/** Les arbres du **créneau** désigné. `null` tant qu'aucun n'est choisi : la requête est alors
 * désactivée plutôt que lancée sur un identifiant inventé (ADR-0075). */
export function useTableaux(departId: number | null) {
  return useQuery({
    queryKey: cleTableaux(departId),
    queryFn: () => getTableaux(departId as number),
    enabled: departId !== null,
    refetchInterval: INTERVALLE_POLL_MS,
    // Écran vivant, pas une fiche : ce qu'on relit doit être considéré périmé d'emblée.
    staleTime: 0,
  })
}

/** Les arbres de **plusieurs** créneaux à la fois (E16US004, récapitulatif de journée).
 *
 * La carte de suivi doit couvrir « tous les tours de toutes les phases joués » d'un archer, et un
 * archer appartient à **un** départ (ADR-0075) qui n'est pas forcément celui que la salle tire :
 * lire le seul créneau en cours amputait le récapitulatif d'un archer du matin dès l'après-midi.
 *
 * ⚠️ **La liste passée doit rester celle des départs réellement concernés**, dérivée des plans déjà
 * chargés — pas « tous les départs du tournoi ». Chaque entrée est une reconstruction serveur
 * complète (`# DETTE-031` ci-dessus) : la borne est ce qui empêche cette commodité de devenir une
 * aggravation de la dette. En pratique un départ, deux si l'on suit des archers de deux créneaux.
 */
export function useTableauxDesDeparts(departIds: number[]) {
  return useQueries({
    queries: departIds.map((departId) => ({
      queryKey: cleTableaux(departId),
      queryFn: () => getTableaux(departId),
      refetchInterval: INTERVALLE_POLL_MS,
      staleTime: 0,
    })),
  })
}
