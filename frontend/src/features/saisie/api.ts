// Accès HTTP de la saisie de qualification (E04US002) — poste de cible / marqueur.
//
// Miroir des DTO du router backend `/api/v1/saisie` (tranche « exposition ») et des endpoints de
// **contexte** (barème, grain, départs) — publics, donc portée `'aucune'`. Les endpoints de saisie
// exigent le **jeton de poste** (`X-Jeton-Poste`) : portée `'poste'` (le client l'injecte, cf.
// `shared/stores/sessionPosteStore`). La **validation** et la **correction** relèvent du scoreur
// (surface distincte, §7.3 du CDC UX) — hors de cette feature.

import { fetchJson } from '../../shared/api/client'

// --- DTO (miroir backend) ---

// Une ligne de la grille : l'archer à une position, et son **pavé** (les zones légales de son
// blason, touches illégales absentes — CA « pavé »). `zones` vide = pavé indisponible (blason non
// configuré) : le serveur reste l'autorité, le front n'affiche que ce qu'il reçoit.
export interface LigneGrille {
  position: string
  archer_id: number
  nom: string
  prenom: string
  zones: string[]
}

// Une volée relue : ses valeurs, le marqueur déclaratif, le verrou (validée par le scoreur) et le
// « quand » (`saisie_le`, ISO 8601). `verrouillee` ⇔ `validee_par` non nul (correction = scoreur).
export interface Volee {
  numero: number
  valeurs: string[]
  saisie_par: string | null
  validee_par: string | null
  verrouillee: boolean
  saisie_le: string | null
  // Purement **local** (E04US009) : la volée est en file hors-ligne, pas encore renvoyée au serveur.
  // Le serveur ne renvoie jamais ce champ ; une volée relue le laisse à `undefined` (donc non en
  // attente). Il alimente l'affichage optimiste (le marqueur avance) et l'annotation « en attente ».
  en_attente?: boolean
}

// L'état d'une série : le cumul (des volées **validées** seulement) et ses volées.
export interface Serie {
  tournoi_id: number
  archer_id: number
  cumul: number
  volees: Volee[]
}

export interface DepartCourant {
  depart_id: number
  numero: number
}

// Barème de la qualification (dimensionne le pavé et le nombre de volées). `null` si non défini.
export interface Bareme {
  nb_volees: number
  nb_fleches_par_volee: number
  nb_fleches_total: number
  score_max: number
}

export type TypeGrain = 'fin_de_serie' | 'fin_de_duel' | 'toutes_les_n_volees'

// Grain de validation de la phase (D-11) : dit au marqueur **quand** le scoreur viendra valider.
export interface Grain {
  grain: TypeGrain
  n_volees: number | null
}

// Un départ du tournoi (sélecteur de « mode départ X » du poste). Sous-ensemble de `departs/api`.
export interface DepartPoste {
  id: number
  numero: number
  horaire: string | null
}

// Corps de saisie d'une volée. `identifiant_saisie` rend l'écriture **idempotente** (ADR-0036) :
// un rejeu réseau du même geste ne saisit pas deux fois.
export interface SaisirVolee {
  tournoi_id: number
  archer_id: number
  numero: number
  valeurs: string[]
  saisie_par: string | null
  identifiant_saisie: string
}

// --- Contexte (endpoints publics) ---

export function getBareme(tournoiId: number): Promise<Bareme | null> {
  return fetchJson<Bareme | null>(
    `/api/v1/tournois/${tournoiId}/bareme-qualification`,
    undefined,
    'aucune',
  )
}

export function getGrain(tournoiId: number): Promise<Grain | null> {
  return fetchJson<Grain | null>(
    `/api/v1/tournois/${tournoiId}/grain-validation`,
    undefined,
    'aucune',
  )
}

// Départs du tournoi : endpoint public (aucune garde côté serveur), lu sans jeton par le poste.
export function getDepartsDuPoste(tournoiId: number): Promise<DepartPoste[]> {
  return fetchJson<DepartPoste[]>(`/api/v1/tournois/${tournoiId}/departs`, undefined, 'aucune')
}

// --- Poste (jeton X-Jeton-Poste) ---

export function fixerDepartCourant(departId: number): Promise<DepartCourant> {
  return fetchJson<DepartCourant>(
    '/api/v1/saisie/depart-courant',
    { method: 'POST', body: JSON.stringify({ depart_id: departId }) },
    'poste',
  )
}

export function getGrille(): Promise<LigneGrille[]> {
  return fetchJson<LigneGrille[]>('/api/v1/saisie/archers', undefined, 'poste')
}

export function getSerie(tournoiId: number, archerId: number): Promise<Serie> {
  return fetchJson<Serie>(`/api/v1/saisie/series/${tournoiId}/${archerId}`, undefined, 'poste')
}

export function saisirVolee(corps: SaisirVolee): Promise<Serie> {
  return fetchJson<Serie>(
    '/api/v1/saisie/volees',
    { method: 'POST', body: JSON.stringify(corps) },
    'poste',
  )
}
