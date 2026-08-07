// Hooks React Query de la feature « departs » (E02US004, ADR-0017).
//
// La liste des départs d'un tournoi est de l'état **serveur** (lecture) ; créer/éditer/supprimer
// sont des **mutations** qui invalident cette liste (rafraîchissement immédiat, en plus de la
// diffusion temps réel post-commit côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  creerDepart,
  getDeparts,
  type ModifierDepart,
  modifierDepart,
  type NouveauDepart,
  supprimerDepart,
} from './api'
import { creneauDesDuels, creneauRetenu } from './libelle'

const cleDeparts = (tournoiId: number) => ['departs', tournoiId] as const

// `enabled` (défaut `true`) : la recherche de la sidebar admin (E12US006), montée sur tout écran, ne
// charge les départs que lorsqu'on cherche — les écrans existants ne passent rien et gardent leur
// comportement.
export function useDeparts(tournoiId: number, enabled = true) {
  return useQuery({
    queryKey: cleDeparts(tournoiId),
    queryFn: () => getDeparts(tournoiId),
    enabled,
  })
}

/** Le créneau des trois écrans de duels : un défaut **calculé une fois**, puis figé.
 *
 * ⚠️ **Le gel n'est pas un détail d'implémentation, c'est le correctif** (2ᵉ revue E01US025).
 * `shared/realtime/useRealtime` appelle `invalidateQueries()` **sans clé** à chaque événement temps
 * réel : la liste des départs est donc refetchée en permanence, et leur `etat` change en cours de
 * journée. Un défaut recalculé à chaque rendu suivait ces changements — le scoreur qui avait ouvert
 * son tableau à 10h55 et n'avait touché à rien voyait, à la clôture de la qualification, l'écran
 * changer de créneau **sous ses doigts** : la clé de requête bascule, `phases.data` redevient
 * indéfini, le tableau se démonte au milieu d'un duel. Sur l'écran qui porte la file hors-ligne,
 * c'est la pire surface possible pour un démontage non sollicité.
 *
 * Une fois le premier créneau résolu, il devient donc un choix **explicite** : plus rien ne le
 * déplace sauf l'utilisateur, ou sa disparition (`creneauRetenu` retombe alors sur le défaut).
 *
 * Hissé en hook partagé à la **3ᵉ occurrence réelle** (plan de duels, saisie des duels, feu vert) —
 * le seuil que le projet se fixe. Recopier le `useEffect` trois fois, c'était garantir qu'un des
 * trois divergerait.
 */
export function useCreneauDesDuels(tournoiId: number) {
  const [choix, setChoix] = useState<number | null>(null)
  const departs = useDeparts(tournoiId)
  const liste = departs.data ?? []
  // ⚠️ **Ajustement pendant le rendu, pas dans un `useEffect`.** C'est le patron que React
  // documente pour dériver un état d'une donnée qui arrive après coup (« You might not need an
  // Effect ») : le `setChoix` ci-dessous relance le rendu **avant** que quoi que ce soit ne soit
  // commité, là où un effet aurait produit un rendu en cascade — ce que le lint refuse, à raison.
  // La garde `choix === null` le rend idempotent : il ne s'exécute qu'une fois, à l'arrivée des
  // créneaux.
  const defaut = creneauDesDuels(liste)?.id ?? null
  if (choix === null && defaut !== null) setChoix(defaut)
  return {
    departs,
    liste,
    departId: creneauRetenu(liste, choix, creneauDesDuels),
    choisir: setChoix,
  }
}

export function useCreerDepart(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (entree: NouveauDepart) => creerDepart(tournoiId, entree),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleDeparts(tournoiId) }),
  })
}

export function useModifierDepart(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    // `confirmeCycle` : rejoue l'édition d'un créneau lancé/clos après le signalement
    // `depart_en_cours_non_confirme` (E12US008).
    mutationFn: ({
      departId,
      entree,
      confirmeCycle,
    }: {
      departId: number
      entree: ModifierDepart
      confirmeCycle?: boolean
    }) => modifierDepart(tournoiId, departId, entree, confirmeCycle),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleDeparts(tournoiId) }),
  })
}

export function useSupprimerDepart(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    // `confirmeCycle` (créneau lancé/clos, E12US008) et `autoriserSuppressionInscrits` (créneau
    // ouvert à inscriptions, ADR-0018) lèvent chacun leur signalement respectif.
    mutationFn: ({
      departId,
      autoriserSuppressionInscrits,
      confirmeCycle,
    }: {
      departId: number
      autoriserSuppressionInscrits?: boolean
      confirmeCycle?: boolean
    }) => supprimerDepart(tournoiId, departId, autoriserSuppressionInscrits, confirmeCycle),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleDeparts(tournoiId) }),
  })
}
