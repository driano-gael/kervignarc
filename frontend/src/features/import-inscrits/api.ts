// Import d'un fichier d'inscrits (E02US007, ADR-0115). Miroir d'`api/v1/import_inscrits.py`.
// Le corps **est** le fichier (comme le logo) : la confirmation le redépose, le serveur ne garde
// rien entre les deux appels.

import { fetchJson } from '../../shared/api/client'

export type DecisionImport = 'creer' | 'inscrire' | 'homonyme' | 'rejetee'

export interface LigneRapport {
  numero: number
  decision: DecisionImport
  motif: string | null
  nom: string | null
  prenom: string | null
  licence: string | null
  depart_numero: number | null
  categorie_id: number | null
  club: string | null
  club_a_creer: boolean
  homonyme_de: string | null
  // INSCRIRE : la fiche que la licence désigne — Résult'Arc ne porte aucun nom.
  fiche: string | null
}

export interface RapportImport {
  source: 'ianseo' | 'resultarc'
  importables: number
  rejetees: number
  homonymes: number
  colonnes_ignorees: string[]
  lignes: LigneRapport[]
}

const enTeteFichier = { 'Content-Type': 'application/octet-stream' }

export function apercuImport(tournoiId: number, fichier: File): Promise<RapportImport> {
  return fetchJson<RapportImport>(`/api/v1/tournois/${tournoiId}/import-inscrits/apercu`, {
    method: 'POST',
    body: fichier,
    headers: enTeteFichier,
  })
}

export function confirmerImport(
  tournoiId: number,
  fichier: File,
  homonymes: number[],
): Promise<RapportImport> {
  const parametres = homonymes.map((numero) => `homonymes=${numero}`).join('&')
  return fetchJson<RapportImport>(
    `/api/v1/tournois/${tournoiId}/import-inscrits${parametres ? `?${parametres}` : ''}`,
    { method: 'POST', body: fichier, headers: enTeteFichier },
  )
}
