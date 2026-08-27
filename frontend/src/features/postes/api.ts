// Accès API de la feature « postes » (E04US001, volet **préparation** admin) : préparer et lister les
// codes de cible d'un tournoi. Miroir des DTO exposés par `api/v1/postes.py`. Routes **imbriquées sous
// le tournoi**. La lecture est réservée à l'admin (la réponse porte les **codes**, secrets à imprimer
// puis coller sur les cibles avec leur QR — E09US008).

import { fetchBlob, fetchJson, telechargerFichier } from '../../shared/api/client'

export interface PosteAdmin {
  id: number
  tournoi_id: number
  cible_index: number
  // Code de la cible **généré par le serveur**, à imprimer sous son QR (E09US008) et retaper en
  // secours pour rattacher une tablette (mode d'identité « le lieu », D-13).
  code: string
}

export function getPostes(tournoiId: number): Promise<PosteAdmin[]> {
  return fetchJson<PosteAdmin[]>(`/api/v1/tournois/${tournoiId}/postes`)
}

export function preparerPostes(tournoiId: number): Promise<PosteAdmin[]> {
  // Idempotent : garantit un code par cible du plan sans changer ceux déjà émis (POST → écriture).
  return fetchJson<PosteAdmin[]>(`/api/v1/tournois/${tournoiId}/postes`, { method: 'POST' })
}

// Image SVG du QR de rattachement d'une cible (E11US008). Chargée en **blob authentifié**
// (`fetchBlob`) : le Bearer admin est en JS, pas un cookie — un `<img src>` direct n'emporterait
// pas le jeton (401). Le blob est converti en **data URL** autoporteuse : une simple chaîne, sans
// objectURL à révoquer, donc aucune fuite mémoire ni piège de cycle de vie sous React StrictMode
// (où un objectURL révoqué au double-montage laisserait l'`<img>` cassé).
export async function getQrCible(tournoiId: number, cibleIndex: number): Promise<string> {
  const blob = await fetchBlob(`/api/v1/tournois/${tournoiId}/postes/${cibleIndex}/qr`)
  return svgEnDataUrl(await blob.text())
}

/** Le PDF des **étiquettes de cible** — une page par cible, QR + code, à découper et à coller.
 *
 * Retour maquettes du 04/08/2026 (A12) : l'affichage à la demande existait, **l'impression en
 * avance, non** — la route était livrée côté serveur (E09US008) mais atteignable depuis aucun
 * écran. C'était une fonctionnalité complète, payée, et invisible. `fetchBlob` et non un `<a
 * href>` : la route est admin et le Bearer vit en JS, pas dans un cookie.
 */
export async function telechargerEtiquettesQr(tournoiId: number): Promise<void> {
  const blob = await fetchBlob(`/api/v1/tournois/${tournoiId}/postes/etiquettes-qr`)
  telechargerFichier(blob, `etiquettes-qr-tournoi-${tournoiId}.pdf`)
}

// Construit la data URL d'un SVG pour un `<img src>`. `encodeURIComponent` échappe tout le contenu
// (`#`, `&`, espaces, `%`…) : aucun caractère du SVG ne peut refermer ou détourner le contexte de
// la data URL. Logique **pure**, extraite pour être verrouillée par un test (patron du projet).
export function svgEnDataUrl(svg: string): string {
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}
