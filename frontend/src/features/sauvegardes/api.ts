// Accès API de la feature « sauvegardes » (E11US006, ADR-0119) — routes admin, hors tournoi.

import { fetchJson } from '../../shared/api/client'

export type NatureSauvegarde = 'periodique' | 'avant_restauration'
export type VerdictSauvegarde = 'restaurable' | 'corrompue' | 'version_differente'

export interface Sauvegarde {
  nom: string
  nature: NatureSauvegarde
  prise_le: string
  taille_octets: number
}

export interface Verification {
  nom: string
  verdict: VerdictSauvegarde
}

export interface Restauration {
  restauree: string
  copie_de_securite: string
}

const racine = (nom: string) => `/api/v1/sauvegardes/${encodeURIComponent(nom)}`

export function getSauvegardes(): Promise<Sauvegarde[]> {
  return fetchJson<Sauvegarde[]>('/api/v1/sauvegardes')
}

export function verifierSauvegarde(nom: string): Promise<Verification> {
  return fetchJson<Verification>(`${racine(nom)}/verification`, { method: 'POST' })
}

export function restaurerSauvegarde(nom: string): Promise<Restauration> {
  return fetchJson<Restauration>(`${racine(nom)}/restauration`, { method: 'POST' })
}
