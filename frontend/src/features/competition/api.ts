// Accès API de la feature « competition » (E00US011) : le fil rouge du walking skeleton —
// créer un tournoi, inscrire/placer un archer, saisir un score, lire le classement.
// Miroir des DTO exposés par `api/v1/competition.py` et `api/v1/tournois.py`.

import { fetchJson } from '../../shared/api/client'

export type TypeTournoi = 'officiel' | 'non_officiel'

// Cycle de vie d'un tournoi à **sept statuts** (E01US017, ADR-0026 ; front aligné en E14US001) :
// brouillon ⇄ prêt → en_cours ⇄ en_pause → terminé → archivé ; annulé est terminal (depuis
// brouillon/prêt/en_cours/en_pause). Le front ne connaissait que les 3 statuts d'E01US002 : dès
// qu'un tournoi atteignait `pret`/`en_pause`/… le badge et le pilotage étaient muets — d'où cet
// alignement. La topologie des transitions offertes est lue via la feature « accueil ».
export type StatutTournoi =
  'brouillon' | 'pret' | 'en_cours' | 'en_pause' | 'termine' | 'archive' | 'annule'

export interface Tournoi {
  id: number
  nom: string
  date: string // ISO (AAAA-MM-JJ)
  lieu: string | null
  type_tournoi: TypeTournoi
  statut: StatutTournoi
  // Le tarif n'est plus au tournoi : il vit sur chaque départ (créneau), feature « departs »
  // (E02US004, ADR-0017).
}

export interface NouveauTournoi {
  nom: string
  date: string
  lieu?: string | null
  type_tournoi?: TypeTournoi
}

// L'édition porte sur les métadonnées uniquement ; le statut évolue via démarrer/terminer.
export type ModifierTournoi = NouveauTournoi

export interface Archer {
  id: number
  tournoi_id: number
  nom: string
  prenom: string
  categorie_id: number
  cible: number | null
  club_id: number | null
  // Handicap (E05US015) : le `officiel` est entretenu par le club, la `surcharge` le prime pour
  // cette édition. `handicap` est le **dérivé** que le serveur calcule (surcharge ?? officiel ?? 0)
  // — on l'affiche tel quel plutôt que de refaire la règle de priorité dans chaque écran.
  handicap_officiel: number | null
  handicap_surcharge: number | null
  handicap: number
}

// Inscription d'un archer (E02US002). `categorie_id` est **obligatoire** ; `club_id` reste
// facultatif : `null` = club encore **inconnu**, jamais « aucun club » — en FFTA tout licencié en
// a un (ADR-0014). L'archer s'inscrit quand même, et l'écran signale l'anomalie à compléter.
export interface NouvelArcher {
  nom: string
  prenom: string
  categorie_id: number
  club_id: number | null
  // Confirmation de l'admin après un refus `homonyme_archer` (409) : déclare que ce nouvel
  // archer, malgré des nom/prénom/club identiques à un inscrit, est bien une autre personne.
  autoriser_homonyme?: boolean
}

// Statut d'un archer dans le classement (E04US015, ADR-0050) : `en_lice` (concourt), `abandon`
// (relégué en fin, rangé) ou `disqualifie` (sorti du classement — rangs `null`, score conservé).
export type StatutClassement = 'en_lice' | 'abandon' | 'disqualifie'

// Classement de qualification (E06US001). Deux rangs : `rang_scratch` (global, toutes catégories)
// et `rang_categorie` (au sein de la catégorie de l'archer). `nb_dix`/`nb_neuf` rendent le départage
// FFTA **traçable** (à total égal, plus de 10 puis de 9 — `docs/referentiel-ffta.md` §8.1). Les
// rangs sont **nullables** : `null` = archer disqualifié (E04US015), hors classement mais listé.
export interface LigneClassement {
  rang_scratch: number | null
  rang_categorie: number | null
  archer_id: number
  nom: string
  prenom: string
  categorie_id: number
  categorie_libelle: string
  cible: number | null
  // `null` = club encore **inconnu** (ADR-0014) : l'écran le signale pour qu'il soit complété.
  club_id: number | null
  total: number
  nb_dix: number
  nb_neuf: number
  statut: StatutClassement
}

// Un ex æquo que le format veut voir tranché **au tir** (E06US003, ADR-0066). Vide tant qu'aucun
// seuil de barrage n'est réglé sur la phase de qualification : le défaut reste le rang partagé.
// `rang` est le rang **partagé** que le barrage va éclater en rangs consécutifs.
export interface EgaliteADepartager {
  rang: number
  archer_ids: number[]
}

export interface Classement {
  tournoi_id: number
  lignes: LigneClassement[]
  egalites_a_departager: EgaliteADepartager[]
}

// --- barrage de places décisives (E06US003, ADR-0066) ---

// ⚠️ `score` **nul** = **absent** au barrage annoncé, pas « pas encore saisi » : l'absence est une
// issue réglementaire (B.6.5.2.4, l'archer est déclaré perdant). Une flèche pas encore notée ne
// s'envoie pas du tout. `distance_au_centre` est en **dixièmes de millimètre** ; nulle = mesure non
// faite, sur laquelle le moteur refuse de départager (il fait retirer) — le cas le plus fréquent.
export interface TirBarrage {
  archer_id: number
  score: number | null
  distance_au_centre: number | null
}

// `ordre` porte le verdict quand tout est départagé ; **vide** sinon, `groupes_a_rejouer` nommant
// alors qui doit retirer. Les deux sont exclusifs, et les groupes ne sont **pas aplatis** : un
// barrage à quatre dont deux à 10 et deux à 8 laisse deux égalités distinctes, qui se retirent
// séparément — les fusionner ferait passer un tireur à 8 devant un tireur à 10 déjà départagé.
// `portee` est une énumération **fermée** côté serveur : on la type comme telle plutôt que
// `string`, au même titre que `StatutClassement`.
export type PorteeBarrage = 'qualification' | 'poule' | 'big_shoot_off'

export interface Barrage {
  id: number
  // ⚠️ **Le barrage pend au créneau, plus au tournoi** (E01US025, ADR-0075) : une place se dispute
  // dans le classement d'un départ. Le champ s'appelait `tournoi_id` et lisait déjà un identifiant
  // de départ — la confusion que `DETTE-044` décrit, invisible au typage des deux côtés.
  depart_id: number
  portee: PorteeBarrage
  rang_dispute: number | null
  // Numéro de poule ou de manche. Le **seul** champ qui distingue deux barrages de même portée :
  // il entre dans l'identité côté serveur, donc il doit être affiché.
  reference: string | null
  // Le groupe d'ex æquo a changé depuis l'annonce : le verdict de ce barrage sera **écarté** du
  // classement. L'écran doit le dire au lieu de laisser saisir un groupe qui n'oppose plus les
  // bonnes personnes.
  perime: boolean
  // L'agrégat en base ne se relit pas (saisie corrompue, écriture directe). Le barrage reste
  // **listé et actionnable** plutôt que de faire tomber tout le panneau en 422.
  incoherent: boolean
  participants: number[]
  manches: TirBarrage[][]
  clos: boolean
  est_resolu: boolean
  ordre: number[]
  groupes_a_rejouer: number[][]
}

export function getBarrages(tournoiId: number): Promise<Barrage[]> {
  return fetchJson<Barrage[]>(`/api/v1/tournois/${tournoiId}/barrages`)
}

// Deux régimes d'annonce (ADR-0066) : en **qualification** les tireurs sont dérivés du classement
// (seul `rang` est requis, et seule une égalité signalée est annonçable) ; en **poule** et en **Big
// Shoot Off** ils sont **désignés**, faute de classement calculé où les lire (DETTE-028).
export interface AnnonceBarrage {
  /** Le créneau où se tire ce barrage — **obligatoire** (ADR-0075).
   *
   * Deux créneaux ont des classements distincts, donc « le rang 3 » ne désigne rien sans lui. Le
   * serveur le refuse en 422 s'il manque : c'est ce qui rendait l'annonce inopérante tant que ce
   * champ n'existait pas côté client. */
  depart_id: number
  rang?: number | null
  portee?: PorteeBarrage
  archer_ids?: number[]
  phase_id?: number | null
  reference?: string | null
}

export function annoncerBarrage(tournoiId: number, annonce: AnnonceBarrage): Promise<Barrage> {
  return fetchJson<Barrage>(`/api/v1/tournois/${tournoiId}/barrages`, {
    method: 'POST',
    body: JSON.stringify(annonce),
  })
}

// `manche` omis = la suivante ; fourni = la manche à **corriger** (le verdict n'est jamais stocké,
// il se recalcule depuis les tirs — donc corriger une flèche corrige le classement).
export function saisirMancheBarrage(
  tournoiId: number,
  barrageId: number,
  tirs: TirBarrage[],
  manche?: number,
): Promise<Barrage> {
  return fetchJson<Barrage>(`/api/v1/tournois/${tournoiId}/barrages/${barrageId}/manche`, {
    method: 'PUT',
    body: JSON.stringify({ tirs, manche }),
  })
}

export function annulerBarrage(tournoiId: number, barrageId: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/barrages/${barrageId}`, {
    method: 'DELETE',
  })
}

export function cloreBarrage(tournoiId: number, barrageId: number): Promise<Barrage> {
  return fetchJson<Barrage>(`/api/v1/tournois/${tournoiId}/barrages/${barrageId}/cloture`, {
    method: 'POST',
  })
}

export function creerTournoi(entree: NouveauTournoi): Promise<Tournoi> {
  return fetchJson<Tournoi>('/api/v1/tournois', {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function getTournois(): Promise<Tournoi[]> {
  return fetchJson<Tournoi[]>('/api/v1/tournois')
}

export function modifierTournoi(id: number, entree: ModifierTournoi): Promise<Tournoi> {
  return fetchJson<Tournoi>(`/api/v1/tournois/${id}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

// Le pilotage du cycle de vie passe désormais par la feature « accueil » (transitions génériques,
// E14US001) : `demarrer` en particulier n'est plus une transition depuis `brouillon` mais depuis
// `prêt` (ADR-0026). `terminer` reste ici car la **complétude** (E12US005) le déclenche avec son
// message chiffré d'avertissement — une voie d'écriture distincte de la frise.
export function terminerTournoi(id: number): Promise<Tournoi> {
  return fetchJson<Tournoi>(`/api/v1/tournois/${id}/terminer`, { method: 'POST' })
}

export function supprimerTournoi(id: number): Promise<void> {
  return fetchJson<void>(`/api/v1/tournois/${id}`, { method: 'DELETE' })
}

export function ajouterArcher(tournoiId: number, entree: NouvelArcher): Promise<Archer> {
  return fetchJson<Archer>(`/api/v1/tournois/${tournoiId}/archers`, {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

export function placerArcher(archerId: number, cible: number): Promise<Archer> {
  return fetchJson<Archer>(`/api/v1/archers/${archerId}/placement`, {
    method: 'POST',
    body: JSON.stringify({ cible }),
  })
}

// Le classement dérive des séries de saisie (E04US002) depuis E06US001 ; l'ancienne écriture de
// score isolé (`saisirScore` du walking skeleton) n'y contribuait plus et a été retirée du front.

// ⚠️ **Le classement est celui d'un créneau, plus du tournoi** (E01US025, ADR-0075). La route
// pendait au tournoi et fusionnait tous les départs : 4 créneaux de 100 archers rendaient un
// classement de 400, où l'archer du matin était rangé contre celui du soir qu'il n'a jamais
// affronté. Un départ rejoue le tournoi en entier, donc il a **son** classement.
//
// `categorieId` optionnel : filtre l'affichage à une catégorie. Les rangs (scratch **et** catégorie)
// restent ceux du classement complet **du départ** — filtrer ne réordonne pas le reste (E06US001).
export function getClassement(departId: number, categorieId?: number): Promise<Classement> {
  const requete =
    categorieId === undefined ? '' : `?categorie_id=${encodeURIComponent(categorieId)}`
  return fetchJson<Classement>(`/api/v1/departs/${departId}/classement${requete}`)
}
