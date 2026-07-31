// Accès API de la feature « patrimoine » (E01US023, ADR-0060) : la bibliothèque de briques du club,
// l'assemblage d'un tournoi et la promotion. Miroir des DTO exposés par `api/v1/patrimoine.py` et
// `api/v1/formats.py`.
//
// Aucune de ces adresses de bibliothèque ne porte de `tournoiId` — c'est tout l'objet de l'US, et ce
// qui permet enfin à l'axe atelier de tenir sa promesse « fabriquer, hors tournoi » (DETTE-023).

import { fetchJson } from '../../shared/api/client'
import type { Blason } from '../blasons/api'
import type { Categorie, ModifierCategorie } from '../categories/api'

// D'où vient une brique. Dit la **provenance**, pas la conformité au règlement (ADR-0060 §4) :
// une brique FFTA modifiée reste marquée `ffta`. Sert les deux listes séparées de l'atelier.
export type OrigineBrique = 'ffta' | 'utilisateur'

export interface RapportAssemblage {
  blasons_copies: number
  blasons_ignores: number
  categories_copiees: number
  categories_ignorees: number
}

// —————————————————————————————————————————————————————————————————————————————————————————————
// Bibliothèque
// —————————————————————————————————————————————————————————————————————————————————————————————

export function getCategoriesBibliotheque(): Promise<Categorie[]> {
  return fetchJson<Categorie[]>('/api/v1/categories')
}

export function getBlasonsBibliotheque(): Promise<Blason[]> {
  return fetchJson<Blason[]>('/api/v1/blasons')
}

export interface NouvelleCategorieBibliotheque {
  libelle: string
  arme?: string | null
  blason_id?: number | null
  hauteur_cm?: number
}

export function creerCategorieBibliotheque(
  entree: NouvelleCategorieBibliotheque,
): Promise<Categorie> {
  return fetchJson<Categorie>('/api/v1/categories', {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

// Édition et suppression d'un modèle passent par les routes **à plat** posées en E01US003/E01US005
// (`PUT /categories/{id}`, `DELETE /blasons/{id}`) : elles ne portent déjà pas de tournoi et
// fonctionnent telles quelles sur une brique de bibliothèque. En ouvrir de nouvelles aurait créé
// deux chemins pour un même geste, qui auraient divergé.
// ⚠️ `PUT /categories/{id}` est **total** (ADR-0020) : tout champ omis est **remis à son défaut**
// côté serveur (`ages: []`, `sexe: null`, `blason_id: null`). L'entrée reprend donc `ModifierCategorie`
// en entier — la première version n'envoyait que `libelle`/`arme`/`hauteur_cm` et effaçait
// silencieusement les tranches d'âge, le sexe et le blason par défaut de toute catégorie renommée,
// y compris en bibliothèque, d'où le défaut se propageait à chaque assemblage suivant.
export type ModifierCategorieBibliotheque = ModifierCategorie

export function renommerCategorieBibliotheque(
  id: number,
  entree: ModifierCategorieBibliotheque,
): Promise<Categorie> {
  return fetchJson<Categorie>(`/api/v1/categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

// « En faire une copie pour garder les deux modèles » — l'original reste intact, la copie passe en
// création utilisateur. Face à `renommerCategorieBibliotheque`, qui modifie l'officiel **sur place**
// et le laisse officiel (le règlement évolue, ADR-0060 §4).
export function dupliquerCategorieBibliotheque(id: number, nom: string): Promise<Categorie> {
  return fetchJson<Categorie>(`/api/v1/categories/${id}/duplication`, {
    method: 'POST',
    body: JSON.stringify({ nom }),
  })
}

export function dupliquerBlasonBibliotheque(id: number, nom: string): Promise<Blason> {
  return fetchJson<Blason>(`/api/v1/blasons/${id}/duplication`, {
    method: 'POST',
    body: JSON.stringify({ nom }),
  })
}

export function supprimerCategorieBibliotheque(id: number): Promise<void> {
  return fetchJson<void>(`/api/v1/categories/${id}`, { method: 'DELETE' })
}

export function supprimerBlasonBibliotheque(id: number): Promise<void> {
  return fetchJson<void>(`/api/v1/blasons/${id}`, { method: 'DELETE' })
}

export interface NouveauBlasonBibliotheque {
  nom: string
  taille: number
  capacite: number
}

export function creerBlasonBibliotheque(entree: NouveauBlasonBibliotheque): Promise<Blason> {
  return fetchJson<Blason>('/api/v1/blasons', {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

// Pré-charge le référentiel FFTA **dans la bibliothèque** — une fois pour toutes, et non à chaque
// tournoi (c'est la correction de fond de DETTE-023). Idempotent côté serveur.
export function prechargerFftaBibliotheque(): Promise<RapportAssemblage> {
  return fetchJson<RapportAssemblage>('/api/v1/patrimoine/precharger-ffta', { method: 'POST' })
}

// —————————————————————————————————————————————————————————————————————————————————————————————
// Assemblage d'un tournoi (copie) et promotion (retour)
// —————————————————————————————————————————————————————————————————————————————————————————————

export function assemblerTournoi(tournoiId: number): Promise<RapportAssemblage> {
  return fetchJson<RapportAssemblage>(`/api/v1/tournois/${tournoiId}/assemblage`, {
    method: 'POST',
  })
}

export function promouvoirCategorie(id: number): Promise<Categorie> {
  return fetchJson<Categorie>(`/api/v1/categories/${id}/promotion`, { method: 'POST' })
}

export function promouvoirBlason(id: number): Promise<Blason> {
  return fetchJson<Blason>(`/api/v1/blasons/${id}/promotion`, { method: 'POST' })
}

// —————————————————————————————————————————————————————————————————————————————————————————————
// Formats de tournoi
// —————————————————————————————————————————————————————————————————————————————————————————————

export type TypePhase = 'qualification' | 'elimination_directe' | 'placement'
export type TypeGrain = 'fin_de_serie' | 'fin_de_duel' | 'toutes_les_n_volees'

export interface Bareme {
  nb_volees: number
  nb_fleches_par_volee: number
}

export interface Grain {
  type: TypeGrain
  n_volees: number | null
}

export interface Source {
  ordre_source: number
  rang_debut: number
  rang_fin: number
}

// Une étape d'un format : tout ce qu'une phase porte, **sauf** son tournoi et son statut — ils
// n'existent pas sur le modèle et naissent à l'application (ADR-0060 §5).
export interface Etape {
  ordre: number
  type: TypePhase
  bareme: Bareme | null
  validation: Grain | null
  source: Source | null
  effectif: number | null
}

export interface FormatTournoi {
  id: number
  nom: string
  origine: OrigineBrique
  etapes: Etape[]
}

export interface NouveauFormat {
  nom: string
  etapes: Etape[]
}

export function getFormats(): Promise<FormatTournoi[]> {
  return fetchJson<FormatTournoi[]>('/api/v1/formats')
}

export function creerFormat(entree: NouveauFormat): Promise<FormatTournoi> {
  return fetchJson<FormatTournoi>('/api/v1/formats', {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function modifierFormat(id: number, entree: NouveauFormat): Promise<FormatTournoi> {
  return fetchJson<FormatTournoi>(`/api/v1/formats/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

// « En faire une copie pour garder les deux modèles » — l'original reste intact, la copie passe en
// création utilisateur. Face à `modifierFormat`, qui est l'issue « modifier l'officiel sur place ».
export function dupliquerFormat(id: number, nom: string): Promise<FormatTournoi> {
  return fetchJson<FormatTournoi>(`/api/v1/formats/${id}/duplication`, {
    method: 'POST',
    body: JSON.stringify({ nom }),
  })
}

export function supprimerFormat(id: number): Promise<void> {
  return fetchJson<void>(`/api/v1/formats/${id}`, { method: 'DELETE' })
}

export function prechargerPresetsFormats(): Promise<FormatTournoi[]> {
  return fetchJson<FormatTournoi[]>('/api/v1/formats/precharger-presets', { method: 'POST' })
}

// Applique un format au tournoi : **crée ses phases**. Remplace la séquence existante ; le serveur
// refuse (409 `phases_engagees`) si une phase n'est plus « à venir ».
export function appliquerFormat(tournoiId: number, formatId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/format`, {
    method: 'PUT',
    body: JSON.stringify({ format_id: formatId }),
  })
}

// Capture le déroulé du tournoi en format de bibliothèque (« ce format est permanent »).
export function promouvoirFormat(tournoiId: number, nom: string): Promise<FormatTournoi> {
  return fetchJson<FormatTournoi>(`/api/v1/tournois/${tournoiId}/format/promotion`, {
    method: 'POST',
    body: JSON.stringify({ nom }),
  })
}

// —————————————————————————————————————————————————————————————————————————————————————————————
// Import du référentiel des clubs
// —————————————————————————————————————————————————————————————————————————————————————————————

export interface RapportImportClubs {
  crees: string[]
  doublons: string[]
  lignes_ignorees: number
}

// Une ligne = un club. Le texte est envoyé **brut** : c'est le serveur qui découpe, replie la casse
// et les accents (`cle_nom`) — dupliquer ce découpage ici ouvrirait la porte que le formulaire ferme.
export function importerClubs(lignes: string): Promise<RapportImportClubs> {
  return fetchJson<RapportImportClubs>('/api/v1/clubs/import', {
    method: 'POST',
    body: JSON.stringify({ lignes }),
  })
}
