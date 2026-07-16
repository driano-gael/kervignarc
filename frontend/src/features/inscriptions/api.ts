// Accès API de la feature « inscriptions » (E02US009, ADR-0017) : lien archer ↔ départ (créneau).
// Miroir des DTO exposés par `api/v1/inscriptions.py`. Deux racines, comme côté serveur : la
// création et la liste sont sous l'archer, la mutation d'une inscription est à plat sur sa ressource.

import { fetchJson } from '../../shared/api/client'

export interface Inscription {
  id: number
  archer_id: number
  depart_id: number
  numero_depart: number
  // Libellé de créneau du départ (ex. « 9h00 »), `null` s'il n'a pas été précisé.
  horaire: string | null
  paye: boolean
  // Montant dû **dérivé** du tarif du départ (ADR-0017), en **centimes entiers** — mise en forme
  // par `../competition/format`. Ce n'est pas un champ stocké de l'inscription.
  montant_du_centimes: number
}

export function getInscriptions(archerId: number): Promise<Inscription[]> {
  return fetchJson<Inscription[]>(`/api/v1/archers/${archerId}/inscriptions`)
}

export function inscrire(archerId: number, departId: number): Promise<Inscription> {
  return fetchJson<Inscription>(`/api/v1/archers/${archerId}/inscriptions`, {
    method: 'POST',
    body: JSON.stringify({ depart_id: departId }),
  })
}

export function marquerPaye(inscriptionId: number, paye: boolean): Promise<Inscription> {
  return fetchJson<Inscription>(`/api/v1/inscriptions/${inscriptionId}`, {
    method: 'PUT',
    body: JSON.stringify({ paye }),
  })
}

export function desinscrire(inscriptionId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/inscriptions/${inscriptionId}`, { method: 'DELETE' })
}
