// Hooks React Query de la recherche transverse (E16US010).
//
// **Chargement paresseux** : la sidebar est montée sur *tout* écran admin — on ne requête qu'avec
// une saisie non vide. `placeholderData` garde les résultats précédents pendant la frappe, sinon
// la liste clignote entre chaque caractère.

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { chercher, type EntiteRecherchable } from './api'

export function cleRecherche(entite: EntiteRecherchable, q: string, tournoiId: number | null) {
  return ['recherche', entite, q, tournoiId] as const
}

export function useRecherche(entite: EntiteRecherchable, q: string, tournoiId: number | null) {
  const fragment = q.trim()
  return useQuery({
    queryKey: cleRecherche(entite, fragment, tournoiId),
    queryFn: () => chercher(entite, fragment, tournoiId),
    enabled: fragment !== '',
    placeholderData: keepPreviousData,
    // Le référentiel bouge peu pendant qu'on cherche ; sans cela, chaque retour d'onglet
    // relançait **toutes** les clés vivantes de la recherche (`DETTE-092`).
    staleTime: 30_000,
  })
}
