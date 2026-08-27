// Accès API des **écrans de salle** (E07US004, ADR-0064). Miroir des DTO de `api/v1/ecrans.py`.
//
// Deux portées, comme côté serveur :
//
// - `'admin'` pour la préparation et le pilotage (créer, régler, imposer une vue, rendre la main) ;
// - `'poste'` pour l'affichage courant — l'écran **lit** ce qu'il doit montrer, avec son jeton de
//   poste. Le rattachement lui-même passe par `features/poste/api.ts`, inchangé : le CA veut le
//   **même** mécanisme que la tablette de cible, pas un chemin parallèle.

import { fetchJson } from '../../shared/api/client'
import type { ReglagePages } from '../../shared/ui/pagination'

/** Les vues qu'un écran sait afficher — miroir de `domain.ecran.VueEcran`.
 *
 * Le catalogue s'est élargi trois fois (palmarès E06US004, affectations E07US008, tableaux
 * E07US005) **sans une seule migration**, la valeur persistée étant la chaîne et non un rang.
 * Règle qui a tenu à chaque fois : on n'inscrit une vue qu'une fois son écran capable de
 * l'afficher. ⚠️ Le quatrième mouvement **a coûté une migration** (`0047`, E05US031) : `tableaux`
 * est devenue `en_cours`. Persister la chaîne rend un **ajout** gratuit, pas un **renommage**.
 */
export type VueEcran =
  'classement' | 'plan_cibles' | 'suivi_deroule' | 'affectations' | 'palmares' | 'en_cours'

export const LIBELLE_VUE: Record<VueEcran, string> = {
  classement: 'Classement',
  plan_cibles: 'Plan de cibles',
  suivi_deroule: 'Suivi du déroulé',
  affectations: 'Affectations',
  // « En cours » et non « Phases » : c'est le mot que l'organisateur reconnaît sur une liste de
  // vues à programmer, et le même que l'onglet public (règle 3). « Tableaux » était juste tant que
  // la vue ne montrait qu'un arbre ; elle montre désormais la phase qui se joue, quel que soit son
  // format (E05US031, ADR-0089). Sur l'écran projeté, personne n'est là pour en choisir une.
  en_cours: 'En cours',
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
  'en_cours',
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

/** Bornes du réglage de pages — miroir de `domain.ecran` (E16US009). Même parti que les bornes de
 * cadence ci-dessus : le serveur reste l'autorité (422 `nombre_de_noms_par_page_invalide` /
 * `cadence_de_page_invalide`), le front s'en sert pour ne pas offrir un réglage voué au refus. */
export const NOMS_PAR_PAGE_MIN = 5
export const NOMS_PAR_PAGE_MAX = 100
export const CADENCE_PAGE_MIN_S = 5
export const CADENCE_PAGE_MAX_S = 300

/** Miroir du DTO `ReglagePagesDTO`. **Défini dans `shared/ui/pagination.ts`** et ré-exporté ici :
 * ses consommateurs sont les deux vues paginées, dans deux features distinctes, et le définir dans
 * cette feature-ci aurait créé deux arêtes entre features pour un type de deux entiers. */
export type { ReglagePages }

export interface Ecran {
  id: number
  tournoi_id: number
  libelle: string
  code: string
  /** **Toujours** rempli : le serveur résout le déroulé par défaut, le front n'a donc jamais à
   * connaître l'existence d'un défaut ni à afficher « aucune vue ». */
  deroule: VueProgrammee[]
  /** **Toujours** rempli aussi (`pages_effectives`) : c'est ce qui a résorbé `DETTE-039` — le
   * défaut vivait dans le composant qui s'en servait, donc hors de portée de tout réglage. */
  pages: ReglagePages
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
  /** Le réglage de pages de **cet** écran, résolu par le serveur. Il vaut sous contrôle comme hors
   * contrôle : une prise change *ce qu'on montre*, jamais *comment une liste se lit de loin*. */
  pages: ReglagePages
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

/** Fixe le découpage et la cadence des listes projetées par un écran (E16US009).
 *
 * Route **distincte** du déroulé : corriger une cadence de page ne doit pas obliger à renvoyer la
 * séquence de vues entière, donc ne peut pas l'écraser par inadvertance. */
export function reglerPages(
  tournoiId: number,
  posteId: number,
  pages: ReglagePages,
): Promise<Ecran> {
  return fetchJson<Ecran>(`/api/v1/tournois/${tournoiId}/ecrans/${posteId}/pages`, {
    method: 'PUT',
    body: JSON.stringify({ pages }),
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
