// Accès API de la feature « exports » (E09US003, formats E16US007) : télécharge les documents
// imprimables d'un tournoi. Réservé à l'admin (`Depends(exiger_admin)`) : le téléchargement passe
// par `fetchBlob`, qui joint le Bearer — un `<a href>` ne l'emporterait pas (le jeton est en JS).
//
// ⚠️ L'écran ne tient **aucune liste de formats** : elle vient du catalogue servi par
// `GET /api/v1/exports` (ADR-0101). Il tient en revanche les **chemins et les options** de chaque
// document, qui sont de l'IHM — c'est la contrepartie assumée du même ADR.

import { fetchBlob, fetchJson, telechargerFichier } from '../../shared/api/client'

// Ordre d'impression de la liste de placement (miroir de `TriPlacement` côté domaine).
export type TriPlacement = 'cible' | 'nom'

export interface OptionsPlacement {
  tri: TriPlacement
  // `null` = tout le tournoi ; sinon, ne sortir que ce départ (filtre optionnel, CA).
  departId: number | null
}

// Un format proposé par le serveur. `code` sert **aussi** d'extension de fichier (ADR-0101).
export interface FormatExport {
  code: string
  libelle: string
}

export interface EntreeCatalogueExport {
  identifiant: string
  libelle: string
  description: string
  formats: FormatExport[]
}

export function chargerCatalogueExports(): Promise<EntreeCatalogueExport[]> {
  return fetchJson<EntreeCatalogueExport[]>('/api/v1/exports')
}

// Construit le chemin de la liste de placement (fonction **pure** — testée isolément). Le tri est
// toujours joint ; le départ ne l'est que s'il est demandé.
export function cheminPlacement(tournoiId: number, options: OptionsPlacement): string {
  const params = new URLSearchParams({ tri: options.tri })
  if (options.departId !== null) params.set('depart_id', String(options.departId))
  return `/api/v1/tournois/${tournoiId}/listes/placement?${params.toString()}`
}

export function cheminClubPaiement(tournoiId: number): string {
  return `/api/v1/tournois/${tournoiId}/listes/club-paiement`
}

export function cheminFeuilleDeMarque(tournoiId: number, departId: number): string {
  return `/api/v1/tournois/${tournoiId}/departs/${departId}/feuille-de-marque`
}

// Joint le format au chemin, que celui-ci porte déjà des paramètres ou non.
export function avecFormat(chemin: string, format: string): string {
  return `${chemin}${chemin.includes('?') ? '&' : '?'}format=${encodeURIComponent(format)}`
}

// Télécharge un document au format demandé. L'extension du fichier proposé est le **code** du
// format : la même valeur que le serveur emploie dans son `Content-Disposition`, ce qui évite de
// tenir une seconde table d'extensions côté écran.
export async function telechargerExport(
  chemin: string,
  nomSansExtension: string,
  format: string,
): Promise<void> {
  const blob = await fetchBlob(avecFormat(chemin, format))
  telechargerFichier(blob, `${nomSansExtension}.${format}`)
}
