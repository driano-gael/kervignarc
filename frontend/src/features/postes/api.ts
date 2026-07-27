// Accès API de la feature « postes » (E04US001, volet **préparation** admin) : préparer et lister les
// codes de cible d'un tournoi. Miroir des DTO exposés par `api/v1/postes.py`. Routes **imbriquées sous
// le tournoi**. La lecture est réservée à l'admin (la réponse porte les **codes**, secrets à imprimer
// puis coller sur les cibles avec leur QR — E09US008).

import { fetchBlob, fetchJson } from '../../shared/api/client'

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

// Image SVG du QR de rattachement d'une cible (E11US008), affichée à l'écran pour rattacher une
// tablette sans passer par le PDF. Chargée en **blob authentifié** (`fetchBlob`) : le Bearer admin
// est en JS, pas un cookie — un `<img src>` direct n'emporterait pas le jeton (401). Miroir de la
// route PDF `etiquettes-qr`, réservée à l'admin (le QR encode le code, secret d'usage).
export function getQrCible(tournoiId: number, cibleIndex: number): Promise<Blob> {
  return fetchBlob(`/api/v1/tournois/${tournoiId}/postes/${cibleIndex}/qr`)
}
