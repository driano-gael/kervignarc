// Accès API du palmarès (E06US004). Miroir des DTO de `api/v1/palmares.py`.
//
// Portée `'aucune'` : **lecture publique** (contrat E10US001), comme le classement de qualification
// et les affectations. Un palmarès est fait pour être lu par tout le monde — il finit sur l'écran de
// salle, sur le téléphone d'un spectateur et au mur, imprimé.

import { fetchJson } from '../../shared/api/client'

// D'où vient le rang. « 9ᵉ » n'a pas le même sens selon qu'un duel perdu l'a décidé ou que l'archer
// n'a jamais quitté la qualification : sans cette distinction, l'écran laisserait croire à une
// élimination qui n'a pas eu lieu.
export type OriginePalmares = 'duels' | 'qualification'

export type StatutPalmares = 'en_lice' | 'abandon' | 'disqualifie'

export interface LignePalmares {
  // Les rangs sont des **fourchettes**. `rang_min === rang_max` : le rang est décerné. `5`/`8` :
  // *ex æquo* 5ᵉ-8ᵉ — soit qu'aucun match ne les départagera jamais (tableau tronqué au podium),
  // soit que le duel à venir tranchera. `null` : archer hors classement (disqualifié, ADR-0050).
  rang_min: number | null
  rang_max: number | null
  rang_categorie_min: number | null
  rang_categorie_max: number | null
  archer_id: number
  nom: string
  prenom: string
  categorie_id: number
  categorie_libelle: string
  club_id: number | null
  origine: OriginePalmares
  statut: StatutPalmares
  // Un **match** a décidé ce rang : la seule forme qui vaut une médaille. Ne se déduit
  // pas de `rang_min === rang_max` — la renumérotation rend un rang exact dès qu'un
  // archer est seul de son groupe, ce qui arrive au vainqueur d'une demi-finale avant
  // la finale.
  decerne: boolean
  // Ce qui reste ouvert le sera **au tir** — à distinguer d'un ex æquo définitif, que
  // plus aucun match ne départagera. Les deux se présentent comme une fourchette.
  en_lice: boolean
}

// Ce qu'un podium récompense (E16US014). L'ordre de cette union est celui de l'affichage, et il
// est décidé par le serveur : le front ne retrie jamais les blocs.
export type PorteePodium = 'scratch' | 'categorie' | 'club'

// Une place : le rang **dans la portée du bloc**. Rendu à part de la ligne pour que l'écran n'ait
// pas à choisir entre trois couples de bornes selon la portée — c'est le serveur qui sait laquelle
// s'applique.
export interface PlacePodium {
  rang: number
  ligne: LignePalmares
}

// Un podium : ses rangs **décernés** dans la profondeur réglée. Peut être vide (la finale n'est pas
// tirée) ou partiel (bronze avant l'or, l'usage en salle). `cle` est `null` pour le scratch, qui ne
// regroupe rien.
export interface Podium {
  portee: PorteePodium
  cle: number | null
  libelle: string
  places: PlacePodium[]
  // ⚠️ **L'état du bloc vient du serveur, il ne se recalcule pas ici.** Le client ne voit que les
  // lignes qu'il a demandées — filtre par catégorie compris —, donc un effectif compté à l'écran
  // vient d'une autre population que celle du bloc. C'était la moitié front du bloquant de revue.
  effectif: number
  en_attente: boolean
}

export interface Palmares {
  tournoi_id: number
  podiums: Podium[]
  // Les places récompensées : de quoi savoir si un bloc est complet sans une seconde requête —
  // les surfaces publiques ne lisent jamais le réglage lui-même.
  profondeur_podium: number
  lignes: LignePalmares[]
}

// Ce que le tournoi récompense. La **lecture** est publique comme le palmarès ; seule l'écriture
// est réservée à l'admin.
export interface ReglagePodiums {
  portees: PorteePodium[]
  profondeur: number
}

export function getPalmares(tournoiId: number, categorieId?: number): Promise<Palmares> {
  const parametres = new URLSearchParams()
  if (categorieId != null) parametres.set('categorie_id', String(categorieId))
  return fetchJson<Palmares>(
    `/api/v1/tournois/${tournoiId}/palmares?${parametres}`,
    undefined,
    'aucune',
  )
}

// L'URL du PDF — ouverte dans un onglet, pas récupérée en `fetch` : le document est servi `inline`,
// et le navigateur sait l'afficher et l'imprimer sans qu'on passe par un blob intermédiaire.
export function urlPalmaresPdf(tournoiId: number, categorieId?: number): string {
  const parametres = new URLSearchParams()
  if (categorieId != null) parametres.set('categorie_id', String(categorieId))
  const suffixe = parametres.toString()
  return `/api/v1/tournois/${tournoiId}/palmares.pdf${suffixe ? `?${suffixe}` : ''}`
}

// Le réglage n'est lu que par l'écran d'admin : portée par défaut, comme `getCloisonnement`. La
// route est ouverte côté serveur (le palmarès l'est), mais aucune surface publique ne l'appelle —
// les blocs arrivent déjà composés dans le palmarès.
export function getReglagePodiums(tournoiId: number): Promise<ReglagePodiums> {
  return fetchJson<ReglagePodiums>(`/api/v1/tournois/${tournoiId}/reglage-podiums`)
}

export function putReglagePodiums(
  tournoiId: number,
  reglage: ReglagePodiums,
): Promise<ReglagePodiums> {
  return fetchJson<ReglagePodiums>(`/api/v1/tournois/${tournoiId}/reglage-podiums`, {
    method: 'PUT',
    body: JSON.stringify(reglage),
  })
}
