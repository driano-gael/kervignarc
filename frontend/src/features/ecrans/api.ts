// Accès API des **écrans de salle** (E07US004, ADR-0064). Miroir des DTO de `api/v1/ecrans.py`.
//
// Deux portées, comme côté serveur :
//
// - `'admin'` pour la préparation et le pilotage (créer, régler, imposer une vue, rendre la main) ;
// - `'poste'` pour l'affichage courant — l'écran **lit** ce qu'il doit montrer, avec son jeton de
//   poste. Le rattachement lui-même passe par `features/poste/api.ts`, inchangé : le CA veut le
//   **même** mécanisme que la tablette de cible, pas un chemin parallèle.

import { fetchJson } from '../../shared/api/client'

/** Les vues qu'un écran sait afficher. Miroir de `domain.ecran.VueEcran` — volontairement plus
 * court que le CA : les affectations (E07US008) et les arbres (E07US005) ne sont pas livrés, les
 * offrir au réglage programmerait une page vide. */
export type VueEcran = 'classement' | 'plan_cibles' | 'suivi_deroule'

export const LIBELLE_VUE: Record<VueEcran, string> = {
  classement: 'Classement',
  plan_cibles: 'Plan de cibles',
  suivi_deroule: 'Suivi du déroulé',
}

export const TOUTES_LES_VUES: VueEcran[] = ['classement', 'plan_cibles', 'suivi_deroule']

/** Bornes de cadence — miroir de `domain.ecran.CADENCE_MIN_S`/`CADENCE_MAX_S`. Le serveur reste
 * l'autorité (422 `cadence_ecran_invalide`) ; le front s'en sert seulement pour ne pas offrir un
 * réglage voué au refus. */
export const CADENCE_MIN_S = 5
export const CADENCE_MAX_S = 3600

export interface VueProgrammee {
  vue: VueEcran
  cadence_s: number
}

export interface Ecran {
  id: number
  tournoi_id: number
  libelle: string
  code: string
  /** **Toujours** rempli : le serveur résout le déroulé par défaut, le front n'a donc jamais à
   * connaître l'existence d'un défaut ni à afficher « aucune vue ». */
  deroule: VueProgrammee[]
}

/** Ce que l'écran doit montrer maintenant. **Exactement l'un** de `vues` ou `vue_figee` est
 * renseigné : l'écran n'arbitre jamais. */
export interface Affichage {
  vues: VueProgrammee[] | null
  vue_figee: VueEcran | null
  sous_controle: boolean
  /** Secondes avant reprise automatique du déroulé ; `null` = pas d'échéance. L'écran décompte
   * **en local** à partir de là — la reprise ne dépend donc d'aucun message serveur, ce qui la rend
   * insensible à une coupure réseau (ADR-0064). */
  reste_s: number | null
}

export interface Prise {
  poste_id: number
  vue_figee: VueEcran | null
  reste_s: number | null
  /** `true` quand la prise n'a **aucune** échéance — le CA « jamais un état forcé qu'on oublie ». */
  exige_rappel: boolean
}

export function getEcrans(tournoiId: number): Promise<Ecran[]> {
  return fetchJson<Ecran[]>(`/api/v1/tournois/${tournoiId}/ecrans`)
}

export function creerEcran(tournoiId: number, libelle: string): Promise<Ecran> {
  return fetchJson<Ecran>(`/api/v1/tournois/${tournoiId}/ecrans`, {
    method: 'POST',
    body: JSON.stringify({ libelle }),
  })
}

export function renommerEcran(tournoiId: number, posteId: number, libelle: string): Promise<Ecran> {
  return fetchJson<Ecran>(`/api/v1/tournois/${tournoiId}/ecrans/${posteId}`, {
    method: 'PUT',
    body: JSON.stringify({ libelle }),
  })
}

export function reglerDeroule(
  tournoiId: number,
  posteId: number,
  vues: VueProgrammee[],
): Promise<Ecran> {
  return fetchJson<Ecran>(`/api/v1/tournois/${tournoiId}/ecrans/${posteId}/deroule`, {
    method: 'PUT',
    body: JSON.stringify({ vues }),
  })
}

export function supprimerEcran(tournoiId: number, posteId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/ecrans/${posteId}`, { method: 'DELETE' })
}

/** Impose une vue figée (`vue`) **ou** une autre séquence (`vues`), pour `duree_s` secondes.
 * `duree_s` absent = « jusqu'à ce que je rende la main » (arbitrage Q-UX7). */
export function prendreLeControle(
  tournoiId: number,
  posteId: number,
  consigne: { vue?: VueEcran; vues?: VueProgrammee[]; duree_s?: number },
): Promise<Prise> {
  return fetchJson<Prise>(`/api/v1/tournois/${tournoiId}/ecrans/${posteId}/controle`, {
    method: 'POST',
    body: JSON.stringify(consigne),
  })
}

export function rendreLaMain(tournoiId: number, posteId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/ecrans/${posteId}/controle`, {
    method: 'DELETE',
  })
}

/** Ce que l'écran rattaché doit montrer. Portée `'poste'` : en-tête `X-Jeton-Poste`. */
export function getAffichage(): Promise<Affichage> {
  return fetchJson<Affichage>('/api/v1/ecrans/session/affichage', undefined, 'poste')
}
