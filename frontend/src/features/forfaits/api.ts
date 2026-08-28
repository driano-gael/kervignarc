// Appels d'API des forfaits — abandon / disqualification (E04US015, ADR-0050). Qualification
// (relégation, exclusion) ou duels (l'adversaire passe) ; écritures routées par la file serveur.

// ⚠️ Le défaut de `fetchJson` est `'admin'`, et une requête ne joint qu'**une** identité : toute
// écriture de scoreur doit nommer `'scoreur'` EXPLICITEMENT — l'omettre change l'identité émise
// en silence. Seule la **déclaration en duel** prend la portée en paramètre (le serveur y accepte
// les deux, E16US008) : venue du feu vert elle part en `'admin'`.

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

// ⚠️ Pas de `portee` en paramètre, contrairement à la déclaration : le serveur accepte l'admin
// (`D-15`) mais aucun écran ne l'appelle encore — `DETTE-090`. La portée `'scoreur'` reste donc
// écrite EN DUR — le défaut de `fetchJson` est `'admin'`, l'omettre changerait l'identité de l'appel
// en silence. Le paramètre reviendra avec son appelant admin.
export function annulerForfaitDuel(
  tournoiId: number,
  phaseId: number,
  archerId: number,
): Promise<{ annule: boolean }> {
  return fetchJson<{ annule: boolean }>(
    '/api/v1/forfaits/duel/annulation',
    {
      method: 'POST',
      body: JSON.stringify({ tournoi_id: tournoiId, phase_id: phaseId, archer_id: archerId }),
    },
    'scoreur',
  )
}
