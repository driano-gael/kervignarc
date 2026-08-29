// Accès API de la recherche transverse (E16US010). Miroir des DTO d'`api/v1/recherche.py`.
//
// Une **seule** route paramétrée par l'entité, comme côté serveur : trois fonctions jumelles
// feraient diverger trois contrats pour une même question.

import { fetchJson } from '../../shared/api/client'

export type EntiteRecherchable = 'tournoi' | 'archer' | 'club'

export interface ResultatRecherche {
  entite: EntiteRecherchable
  id: number
  libelle: string
  precision: string | null
  // ⚠️ Le tournoi **où ouvrir la fiche**, pas celui qu'on affiche : `precision` en porte le nom,
  // qui se lit mais ne s'adresse pas. `null` pour un club (référentiel global).
  tournoi_id: number | null
}

export interface Recherche {
  resultats: ResultatRecherche[]
  // Peut dépasser `resultats.length` : la complétion est bornée côté serveur. L'écran doit le
  // dire, sans quoi la liste tronquée se lit « il n'y a que ça ».
  total: number
}

export function chercher(
  entite: EntiteRecherchable,
  q: string,
  tournoiId: number | null,
): Promise<Recherche> {
  const params = new URLSearchParams({ entite, q })
  if (tournoiId !== null) params.set('tournoi_id', String(tournoiId))
  return fetchJson<Recherche>(`/api/v1/recherche?${params.toString()}`)
}
