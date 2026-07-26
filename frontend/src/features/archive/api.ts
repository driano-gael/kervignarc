// Accès API de la feature « archive » (E11US003) : télécharge le paquet ZIP d'archive de fin de
// tournoi (instantané SQLite + CSV de toute la base + PDF régénérés + manifeste), selon les parties
// **cochées**. Réservé à l'admin (route `Depends(exiger_admin)`) : le téléchargement passe par
// `fetchBlob`, qui joint le Bearer admin (un simple `<a href>` ne l'emporterait pas — jeton en JS).

import { fetchBlob, telechargerFichier } from '../../shared/api/client'

// Parties incluses dans l'archive (miroir de `OptionsArchive` côté service). Tout à `true` = archive
// complète (cas nominal). Chaque clé est un paramètre de requête booléen côté endpoint.
export interface OptionsArchive {
  base: boolean
  donneesCsv: boolean
  feuillesDeMarque: boolean
  listePlacement: boolean
  listeClubPaiement: boolean
}

export const OPTIONS_ARCHIVE_DEFAUT: OptionsArchive = {
  base: true,
  donneesCsv: true,
  feuillesDeMarque: true,
  listePlacement: true,
  listeClubPaiement: true,
}

// Construit le chemin de l'archive (fonction **pure** — testée isolément). Les booléens sont
// sérialisés `true`/`false` (FastAPI les relit en `bool`). Les noms de paramètres suivent le snake
// _case de l'endpoint (`donnees_csv`, `feuilles_de_marque`, …).
export function cheminArchive(tournoiId: number, options: OptionsArchive): string {
  const params = new URLSearchParams({
    base: String(options.base),
    donnees_csv: String(options.donneesCsv),
    feuilles_de_marque: String(options.feuillesDeMarque),
    liste_placement: String(options.listePlacement),
    liste_club_paiement: String(options.listeClubPaiement),
  })
  return `/api/v1/tournois/${tournoiId}/archive?${params.toString()}`
}

export async function telechargerArchive(
  tournoiId: number,
  options: OptionsArchive,
): Promise<void> {
  const blob = await fetchBlob(cheminArchive(tournoiId, options))
  telechargerFichier(blob, `archive-tournoi-${tournoiId}.zip`)
}
