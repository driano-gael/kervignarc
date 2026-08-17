// Accès API des **écrans de salle** (E07US004, ADR-0064). Miroir des DTO de `api/v1/ecrans.py`.
//
// Deux portées, comme côté serveur :
//
// - `'admin'` pour la préparation et le pilotage (créer, régler, imposer une vue, rendre la main) ;
// - `'poste'` pour l'affichage courant — l'écran **lit** ce qu'il doit montrer, avec son jeton de
//   poste. Le rattachement lui-même passe par `features/poste/api.ts`, inchangé : le CA veut le
//   **même** mécanisme que la tablette de cible, pas un chemin parallèle.

import { fetchJson } from '../../shared/api/client'

/** Les vues qu'un écran sait afficher. Miroir de `domain.ecran.VueEcran`, qui **couvre désormais le
 * CA d'E07US004 en entier** : le catalogue s'est élargi trois fois — palmarès (E06US004),
 * affectations (E07US008), tableaux (E07US005) — **sans une seule migration**, la valeur persistée
 * étant la chaîne et non un rang. La règle qui a tenu à chaque fois : on n'inscrit une vue qu'une
 * fois son écran capable de l'afficher, sinon le réglage programme une page vide. */
export type VueEcran =
  'classement' | 'plan_cibles' | 'suivi_deroule' | 'affectations' | 'palmares' | 'tableaux'

export const LIBELLE_VUE: Record<VueEcran, string> = {
  classement: 'Classement',
  plan_cibles: 'Plan de cibles',
  suivi_deroule: 'Suivi du déroulé',
  affectations: 'Affectations',
  // ⚠️ **« Rencontres » depuis E05US031** (ADR-0089 §3) — le libellé s'élargit, **la clé reste
  // `tableaux`**. La vue ne projette plus le seul arbre de duels mais la phase qui se joue, quelle
  // que soit sa forme : poules, système suisse, Big Shoot Off. « Tableaux » était devenu faux pour
  // trois formats sur quatre.
  //
  // La clé n'est pas renommée parce qu'elle est **persistée** sur chaque poste-écran (ADR-0064 §3 :
  // le déroulé de vues est un réglage de préparation, en base). La changer imposerait une migration
  // de données pour un mot, et casserait tout déroulé déjà composé. L'écart assumé entre la clé
  // technique et le libellé métier est inscrit au registre (`DETTE-070`) : non écrit, il se
  // redécouvre en cherchant pourquoi un `grep tableaux` ne trouve rien.
  //
  // Sur l'écran projeté, la vue montre la phase **qui se joue** — personne n'est là pour en choisir
  // une.
  tableaux: 'Rencontres',
  // « Palmarès » et non « Podium » : la vue porte les podiums **et** le classement final complet.
  // L'appeler podium ferait croire à quatre lignes, et l'organisateur qui cherche le classement de
  // fin de journée ne le programmerait pas.
  palmares: 'Palmarès',
}

export const TOUTES_LES_VUES: VueEcran[] = [
  'classement',
  'plan_cibles',
  'suivi_deroule',
  'affectations',
  'tableaux',
  'palmares',
]

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
  /** **Toujours** le déroulé propre de l'écran : ce sur quoi il retombe seul à l'échéance, sans
   * rien redemander au serveur. Distinct de `vues`, qui peut porter une séquence **imposée** —
   * les confondre laissait un écran isolé jouer indéfiniment la consigne de l'admin (revue). */
  deroule_repli: VueProgrammee[]
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
