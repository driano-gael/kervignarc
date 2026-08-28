// Appels d'API des forfaits — abandon / disqualification (E04US015, ADR-0050).
//
// Acte du **scoreur** : le jeton `X-Jeton-Scoreur` est joint automatiquement (portée `'scoreur'`,
// cf. `shared/api/client`). Déclarer / annuler en **qualification** (relégation / exclusion au
// classement) ou en **duels** (l'adversaire passe). Écritures routées par la file serveur.
// ⚠️ Les deux appels de **duel** portent une `portee` : le serveur y accepte admin **ou** scoreur
// (E16US008) et une requête ne joint qu'**une** identité à la fois — appelée depuis le feu vert,
// elle doit partir en `'admin'`, faute de quoi elle partirait anonyme.

import { fetchJson, type PorteeAuth } from '../../shared/api/client'

export type NatureForfait = 'abandon' | 'disqualification'

export interface Forfait {
  id: number | null
  tournoi_id: number
  archer_id: number
  phase_id: number
  nature: NatureForfait
  declare_par: string
  declare_le: string
  motif: string | null
}

export function declarerForfaitQualif(
  tournoiId: number,
  archerId: number,
  nature: NatureForfait,
  motif?: string,
): Promise<Forfait> {
  return fetchJson<Forfait>(
    '/api/v1/forfaits/qualification',
    {
      method: 'POST',
      body: JSON.stringify({ tournoi_id: tournoiId, archer_id: archerId, nature, motif }),
    },
    'scoreur',
  )
}

export function annulerForfaitQualif(
  tournoiId: number,
  archerId: number,
): Promise<{ annule: boolean }> {
  return fetchJson<{ annule: boolean }>(
    '/api/v1/forfaits/qualification/annulation',
    { method: 'POST', body: JSON.stringify({ tournoi_id: tournoiId, archer_id: archerId }) },
    'scoreur',
  )
}

export function declarerForfaitDuel(
  tournoiId: number,
  phaseId: number,
  archerId: number,
  nature: NatureForfait,
  motif?: string,
  portee: PorteeAuth = 'scoreur',
): Promise<Forfait> {
  return fetchJson<Forfait>(
    '/api/v1/forfaits/duel',
    {
      method: 'POST',
      body: JSON.stringify({
        tournoi_id: tournoiId,
        phase_id: phaseId,
        archer_id: archerId,
        nature,
        motif,
      }),
    },
    portee,
  )
}

export function annulerForfaitDuel(
  tournoiId: number,
  phaseId: number,
  archerId: number,
  portee: PorteeAuth = 'scoreur',
): Promise<{ annule: boolean }> {
  return fetchJson<{ annule: boolean }>(
    '/api/v1/forfaits/duel/annulation',
    {
      method: 'POST',
      body: JSON.stringify({ tournoi_id: tournoiId, phase_id: phaseId, archer_id: archerId }),
    },
    portee,
  )
}
