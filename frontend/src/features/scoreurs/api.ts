// Accès API de la feature « scoreurs » (E10US003, volet **définition** admin) : CRUD des scoreurs
// d'un tournoi. Miroir des DTO exposés par `api/v1/scoreurs.py`. Routes **imbriquées sous le
// tournoi** (un scoreur appartient à un tournoi) : l'édition et la suppression portent le `tournoiId`.
// La lecture aussi est réservée à l'admin (la réponse porte les **codes**, des secrets à distribuer).

import { fetchBlob, fetchJson, telechargerFichier } from '../../shared/api/client'
import { svgEnDataUrl } from '../../shared/api/svg'

export interface Scoreur {
  id: number
  tournoi_id: number
  nom: string
  // Code individuel **généré par le serveur**, à imprimer et remettre au scoreur : c'est son sésame
  // de connexion (mode d'identité « la personne », D-13). Non modifiable (figé à la création).
  code: string
}

export interface NouveauScoreur {
  // Le nom seul : le code est généré côté serveur. L'édition ne porte que sur le nom (code figé).
  nom: string
}

export function getScoreurs(tournoiId: number): Promise<Scoreur[]> {
  return fetchJson<Scoreur[]>(`/api/v1/tournois/${tournoiId}/scoreurs`)
}

export function creerScoreur(tournoiId: number, entree: NouveauScoreur): Promise<Scoreur> {
  return fetchJson<Scoreur>(`/api/v1/tournois/${tournoiId}/scoreurs`, {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function modifierScoreur(
  tournoiId: number,
  scoreurId: number,
  entree: NouveauScoreur,
): Promise<Scoreur> {
  return fetchJson<Scoreur>(`/api/v1/tournois/${tournoiId}/scoreurs/${scoreurId}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

export function supprimerScoreur(tournoiId: number, scoreurId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/scoreurs/${scoreurId}`, {
    method: 'DELETE',
  })
}

/** Le PDF des **cartes de scoreur** — une page par scoreur : son nom et son code personnel.
 *
 * Retour maquettes du 04/08/2026 (A08) : « garde quand meme la possibilite de pouvoir tous les
 * imprimer ». Comme les etiquettes de cible, la route existait cote serveur (E09US008) sans
 * qu'aucun ecran ne l'atteigne. `fetchBlob` et non un lien : route admin, Bearer en JS, pas en
 * cookie.
 */
export async function telechargerCartesScoreurs(tournoiId: number): Promise<void> {
  const blob = await fetchBlob(`/api/v1/tournois/${tournoiId}/scoreurs/cartes-codes`)
  telechargerFichier(blob, `cartes-scoreurs-tournoi-${tournoiId}.pdf`)
}

// Image SVG du QR de session d'un scoreur (E16US015), jumeau de `getQrCible`. Blob **authentifié**
// (`fetchBlob`) : le Bearer admin vit en JS, un `<img src>` direct rendrait 401. Converti en data
// URL autoporteuse. ⚠️ Le QR encode le **code personnel** du scoreur : ne jamais monter l'appel
// sans geste explicite de l'admin (cf. `useQrScoreur`, appel désarmé par défaut).
export async function getQrScoreur(tournoiId: number, scoreurId: number): Promise<string> {
  const blob = await fetchBlob(`/api/v1/tournois/${tournoiId}/scoreurs/${scoreurId}/qr`)
  return svgEnDataUrl(await blob.text())
}
