// Accès API + hook de suivi du **déroulé du tour** d'un archer (E07US009, ADR-0039).
//
// Miroir du DTO public exposé par `api/v1/deroule.py` : les volées du jour de l'archer suivi, chacune
// avec ses valeurs, son total, un **statut** (« en attente de validation » / « validé ») et son
// horodatage, plus le cumul **validé**. Endpoint public, anonyme — le DTO tait volontairement
// l'identité du scoreur (règle 6). Les scores non validés sont **provisoires** (ADR-0039) : l'UI le
// signale par le statut.
//
// Le live est **gratuit** : cet état serveur React Query est invalidé globalement par la diffusion
// temps réel post-commit (E04US009), donc chaque volée saisie ou validée rafraîchit la carte sans
// action de l'utilisateur.

import { useQuery } from '@tanstack/react-query'
import { fetchJson } from '../../shared/api/client'

// Statut d'une volée, miroir du `Literal` serveur. `en_attente` = saisie mais pas encore verrouillée
// par le scoreur ; `valide` = grain de validation passé (E01US015).
export type StatutVolee = 'en_attente' | 'valide'

export interface VoleeDeroule {
  numero: number
  valeurs: string[]
  points: number
  statut: StatutVolee
  horodatage: string | null
}

export interface Deroule {
  tournoi_id: number
  archer_id: number
  cumul: number
  volees: VoleeDeroule[]
}

export function getDeroule(tournoiId: number, archerId: number): Promise<Deroule> {
  return fetchJson<Deroule>(`/api/v1/tournois/${tournoiId}/archers/${archerId}/deroule`)
}

// Clé de cache dédiée à un (tournoi, archer) : chaque carte suivie a la sienne, invalidée en bloc par
// le temps réel comme le reste du cache public.
export const cleDeroule = (tournoiId: number, archerId: number) =>
  ['deroule', tournoiId, archerId] as const

export function useDeroule(tournoiId: number, archerId: number) {
  return useQuery({
    queryKey: cleDeroule(tournoiId, archerId),
    queryFn: () => getDeroule(tournoiId, archerId),
  })
}
