// Accès API de la feature « exports » (E09US003) : télécharge les listes imprimables (PDF) d'un
// tournoi — liste de placement (accueil) et liste club & paiement (administratif). Réservé à l'admin
// (routes `Depends(exiger_admin)`) : le téléchargement passe donc par `fetchBlob`, qui joint le
// Bearer admin — un simple `<a href>` ne l'emporterait pas (le jeton est en JS, pas un cookie).

import { fetchBlob, telechargerFichier } from '../../shared/api/client'

// Ordre d'impression de la liste de placement (miroir de `TriPlacement` côté domaine).
export type TriPlacement = 'cible' | 'nom'

export interface OptionsPlacement {
  tri: TriPlacement
  // `null` = tout le tournoi ; sinon, ne sortir que ce départ (filtre optionnel, CA).
  departId: number | null
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

export async function telechargerPlacement(
  tournoiId: number,
  options: OptionsPlacement,
): Promise<void> {
  const blob = await fetchBlob(cheminPlacement(tournoiId, options))
  const suffixe = options.departId !== null ? `-depart-${options.departId}` : ''
  telechargerFichier(blob, `placement-tournoi-${tournoiId}${suffixe}.pdf`)
}

export async function telechargerClubPaiement(tournoiId: number): Promise<void> {
  const blob = await fetchBlob(cheminClubPaiement(tournoiId))
  telechargerFichier(blob, `club-paiement-tournoi-${tournoiId}.pdf`)
}
