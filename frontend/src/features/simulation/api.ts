// Accès API du cockpit de simulation (E15US003) — piloter une session de simulation vivante.
//
// Miroir des DTO exposés par `api/v1/simulation.py`. Outil **admin** de démo/QA : les appels partent
// avec le jeton admin (joint par le client). Rien n'est persisté — le serveur ne joue que dans un
// harnais en mémoire (ADR-0054/0055). Le classement et les tableaux réutilisent les types de lecture
// de la compétition (`Classement`) : un même objet se rend partout pareil.

import { fetchJson } from '../../shared/api/client'
import type { Classement } from '../competition/api'

export type EtatPilote = 'en_cours' | 'en_pause' | 'terminee'
export type EtapeSimulation = 'qualification' | 'duels' | 'terminee'
export type Cote = 'haut' | 'bas'

export interface Progression {
  volees_faites: number
  volees_total: number
  duels_faits: number
  duels_total: number
}

export interface DuellisteSimule {
  archer_id: number
  nom: string
  prenom: string
}

export interface ProchaineVolee {
  archer_id: number
  archer_nom: string
  archer_prenom: string
  numero_volee: number
  nb_fleches: number
  zones: string[]
}

export interface ProchaineDuel {
  phase_id: number
  match_numero: number
  tour: number
  haut: DuellisteSimule | null
  bas: DuellisteSimule | null
  mode: string
}

export interface ProchaineUnite {
  genre: 'volee' | 'duel'
  volee: ProchaineVolee | null
  duel: ProchaineDuel | null
}

export interface ResultatDuelSimule {
  vainqueur: Cote | null
  termine: boolean
}

export interface DuelSimule {
  numero: number
  tour: number
  est_bye: boolean
  haut: DuellisteSimule | null
  bas: DuellisteSimule | null
  validee_par: string | null
  resultat: ResultatDuelSimule | null
}

export interface PlaceSimule {
  rang: number
  duelliste: DuellisteSimule
}

export interface TableauSimule {
  effectif: number
  taille: number
  nb_tours: number
  est_termine: boolean
  duels: DuelSimule[]
  podium: PlaceSimule[]
}

export interface EtatSession {
  session_id: number
  tournoi_id: number
  tournoi_nom: string
  graine: number
  etat_pilote: EtatPilote
  etape: EtapeSimulation
  progression: Progression
  classement: Classement
  tableaux: TableauSimule[]
  prochaine_unite: ProchaineUnite | null
}

export interface VoleeSimule {
  numero: number
  valeurs: string[]
  saisie_par: string | null
  validee_par: string | null
  points: number
}

export interface DetailArcher {
  archer_id: number
  nom: string
  prenom: string
  cumul: number
  volees: VoleeSimule[]
}

function poster(chemin: string, corps?: unknown): Promise<EtatSession> {
  return fetchJson<EtatSession>(chemin, {
    method: 'POST',
    body: corps === undefined ? undefined : JSON.stringify(corps),
  })
}

export function demarrer(tournoiId: number, graine?: number): Promise<EtatSession> {
  return poster('/api/v1/simulations', { tournoi_id: tournoiId, graine: graine ?? null })
}

export function etatSession(sessionId: number): Promise<EtatSession> {
  return fetchJson<EtatSession>(`/api/v1/simulations/${sessionId}`)
}

export function avancer(sessionId: number, nbPas = 1): Promise<EtatSession> {
  return poster(`/api/v1/simulations/${sessionId}/avancer`, { nb_pas: nbPas })
}

export function terminer(sessionId: number): Promise<EtatSession> {
  return poster(`/api/v1/simulations/${sessionId}/terminer`)
}

export function pause(sessionId: number): Promise<EtatSession> {
  return poster(`/api/v1/simulations/${sessionId}/pause`)
}

export function reprendre(sessionId: number): Promise<EtatSession> {
  return poster(`/api/v1/simulations/${sessionId}/reprendre`)
}

export function saisirVolee(
  sessionId: number,
  archerId: number,
  numeroVolee: number,
  valeurs: string[],
): Promise<EtatSession> {
  return poster(`/api/v1/simulations/${sessionId}/saisir-volee`, {
    archer_id: archerId,
    numero_volee: numeroVolee,
    valeurs,
  })
}

export function designerVainqueur(
  sessionId: number,
  phaseId: number,
  matchNumero: number,
  cote: Cote,
): Promise<EtatSession> {
  return poster(`/api/v1/simulations/${sessionId}/designer-vainqueur`, {
    phase_id: phaseId,
    match_numero: matchNumero,
    cote,
  })
}

export function detailArcher(sessionId: number, archerId: number): Promise<DetailArcher> {
  return fetchJson<DetailArcher>(`/api/v1/simulations/${sessionId}/archers/${archerId}`)
}

export function arreter(sessionId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/simulations/${sessionId}`, { method: 'DELETE' })
}
