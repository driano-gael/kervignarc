// Accès API de la feature « paiements » (E08US002) : suivi des règlements par archer et par club.
// Miroir des DTO exposés par `api/v1/paiements.py`. Tout est **réservé à l'admin** (les montants ne
// sont pas publics). Les montants sont en **centimes entiers** (ADR-0012), mis en forme à l'écran
// par `../competition/format`.

import { fetchJson } from '../../shared/api/client'

// Récapitulatif dû / payé / reste (le serveur explicite `reste`, la règle métier lui appartient).
export interface RecapPaiement {
  du_centimes: number
  paye_centimes: number
  reste_centimes: number
}

export interface LignePaiementArcher {
  archer_id: number
  nom: string
  prenom: string
  // `null` = archer sans club (regroupé sous « Sans club » dans la vue par club, ADR-0014).
  club_id: number | null
  recap: RecapPaiement
}

export interface RecapClub {
  // `null` = bucket **virtuel** des archers sans club : ni marquable en lot, ni un club réel.
  club_id: number | null
  nom: string
  recap: RecapPaiement
  archers: LignePaiementArcher[]
}

export function getPaiementsArchers(tournoiId: number): Promise<LignePaiementArcher[]> {
  return fetchJson<LignePaiementArcher[]>(`/api/v1/tournois/${tournoiId}/paiements/archers`)
}

export function getPaiementsClubs(tournoiId: number): Promise<RecapClub[]> {
  return fetchJson<RecapClub[]>(`/api/v1/tournois/${tournoiId}/paiements/clubs`)
}

export function marquerArcher(
  tournoiId: number,
  archerId: number,
  paye: boolean,
): Promise<LignePaiementArcher> {
  return fetchJson<LignePaiementArcher>(
    `/api/v1/tournois/${tournoiId}/paiements/archers/${archerId}`,
    { method: 'PUT', body: JSON.stringify({ paye }) },
  )
}

export function marquerClub(tournoiId: number, clubId: number, paye: boolean): Promise<RecapClub> {
  return fetchJson<RecapClub>(`/api/v1/tournois/${tournoiId}/paiements/clubs/${clubId}`, {
    method: 'PUT',
    body: JSON.stringify({ paye }),
  })
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Remboursements (E08US005, ADR-0057) : sommes encaissées à rendre, nées d'une inscription payée
// effacée (désinscription, suppression de départ). Miroir de `api/v1/remboursements.py`.
// ————————————————————————————————————————————————————————————————————————————————————————————————

// Issue de traitement : « remboursé » (argent rendu) ou « reporté » (réaffecté à un autre créneau).
export type IssueRemboursement = 'rembourse' | 'reporte'

export interface Remboursement {
  id: number
  // Instantanés figés à l'ouverture (l'inscription/le départ ont souvent disparu, ADR-0057).
  archer_prenom: string
  archer_nom: string
  creneau: string
  montant_centimes: number
  // `depart_supprime` | `desinscription`.
  motif: string
  // `a_rembourser` | `rembourse` | `reporte`.
  statut: string
  // Dates ISO 8601 (UTC). `traite_le` est `null` tant que le poste est à traiter.
  cree_le: string
  traite_le: string | null
}

export function getRemboursements(tournoiId: number): Promise<Remboursement[]> {
  return fetchJson<Remboursement[]>(`/api/v1/tournois/${tournoiId}/remboursements`)
}

export function traiterRemboursement(
  tournoiId: number,
  remboursementId: number,
  statut: IssueRemboursement,
): Promise<Remboursement> {
  return fetchJson<Remboursement>(
    `/api/v1/tournois/${tournoiId}/remboursements/${remboursementId}`,
    { method: 'PUT', body: JSON.stringify({ statut }) },
  )
}
