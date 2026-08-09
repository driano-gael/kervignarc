// Accès HTTP de la saisie en duels (E04US013) — surface **scoreur** (écran tactile de duel).
//
// Miroir des DTO du router backend `/api/v1/duels` (`saisie_duels.py`). Les routes de duel exigent
// le **jeton scoreur** (`X-Jeton-Scoreur`) : portée `'scoreur'` (le client l'injecte, cf.
// `shared/stores/sessionScoreurStore`). La liste des **phases** est une lecture **publique**
// (E10US001 : `GET /tournois/{id}/phases` n'a pas de garde) : portée `'aucune'` — le scoreur y accède
// sans en-tête, comme n'importe quelle consultation. Le serveur reste l'**autorité** : mode, barème,
// zones, résultat viennent de lui ; le front n'affiche que ce qu'il reçoit (ADR-0049).

import { fetchJson } from '../../shared/api/client'
import type { FamilleDuel } from '../../shared/stores/fileDuelsHorsLigneStore'

// --- DTO (miroir backend) ---

// Un duelliste résolu (depuis le classement) pour l'affichage d'un camp.
export interface Duelliste {
  archer_id: number
  nom: string
  prenom: string
}

// Une manche (« set ») relue : son rang et les deux volées opposées (codes de zone).
export interface Manche {
  numero: number
  haut: string[]
  bas: string[]
}

// Le tir de barrage (shoot-off, §8.2) : une flèche par camp, et le gagnant **désigné** (le plus près
// du centre, jugé par le scoreur) quand les flèches sont à égalité.
export interface Barrage {
  haut: string
  bas: string
  // Le backend n'émet que `'haut'`/`'bas'` (valeur de l'énuméré `Cote`) ou `null` : on resserre le
  // miroir sur `Cote | null` plutôt que `string | null`, pour éviter un cast au point d'usage.
  gagnant_designe: Cote | null
}

// Le camp d'un duelliste (occupants du match, ADR-0028) — l'énuméré `Cote` côté backend.
export type Cote = 'haut' | 'bas'

// L'issue **calculée** du duel (autorité serveur — le front ne recompute pas, ADR-0049) : points de
// chaque camp (points de set en `sets`, cumul de flèches en `cumul`), vainqueur, fin, barrage requis.
export interface Resultat {
  points_haut: number
  points_bas: number
  vainqueur: Cote | null
  termine: boolean
  barrage_requis: boolean
}

export type ModeDuel = 'sets' | 'cumul'

// L'état d'un match du tableau. `mode`, `nb_manches`, `nb_fleches_par_volee`, `points_pour_gagner` et
// `zones` **dimensionnent le pavé** (renseignés dès qu'un match est jouable, avant tout tir ;
// `null`/vides pour un bye ou des occupants inconnus). `manches`/`barrage`/`resultat` n'existent
// qu'une fois un tir saisi. `validee_par` non nul ⇔ duel **verrouillé** (la saisie s'y ferme).
export interface Duel {
  numero: number
  tour: number
  place_en_jeu: number[] | null
  haut: Duelliste | null
  bas: Duelliste | null
  est_bye: boolean
  mode: ModeDuel | null
  nb_manches: number | null
  nb_fleches_par_volee: number | null
  points_pour_gagner: number | null
  zones: string[]
  validee_par: string | null
  manches: Manche[]
  barrage: Barrage | null
  resultat: Resultat | null
  // Purement **local** (E04US009) : un acte de ce duel est en file hors-ligne, pas encore renvoyé.
  // Le serveur ne renvoie jamais ce champ ; il alimente l'annotation « en attente d'envoi ».
  en_attente?: boolean
  // Purement **local** : une **validation** de ce duel est en file hors-ligne. Verrouille l'écran
  // comme le ferait le serveur en ligne (`DuelVerrouille`), pour interdire une réédition de manche
  // postérieure qui serait perdue au rejeu (revue adversariale E04US013). Réconcilié à la relecture.
  validation_en_attente?: boolean
}

// Une place de podium acquise (rang + duelliste).
export interface Place {
  rang: number
  duelliste: Duelliste
}

// La photo du tableau reconstruit : dimensions, matchs (avec tir) et podium acquis.
export interface Tableau {
  effectif: number
  taille: number
  nb_tours: number
  est_termine: boolean
  duels: Duel[]
  podium: Place[]
}

// Une phase **d'un créneau** (sous-ensemble de `features/phases/api` — on ne garde que ce que le
// scoreur consomme : l'id à scorer, l'ordre à afficher, le type pour ne retenir que les tableaux).
//
// ⚠️ **C'est une phase, pas une étape du déroulé** (ADR-0076). Ce type était alimenté par
// `/tournois/{id}/phases`, qui rend depuis lors des `deroule_etape` — structurellement identiques
// (`id`, `ordre`, `type`), donc TypeScript ne voyait rien, et les deux séquences d'`id` coïncident
// sur un tournoi mono-départ. Le scoreur de l'après-midi scorait ainsi le tableau du matin.
export interface Phase {
  id: number
  ordre: number
  type: string
}

// Corps des écritures. `identifiant_saisie` rend l'acte **idempotent** (ADR-0036) : un rejeu réseau
// du même geste ne l'enregistre pas deux fois (clé scopée opération + cible côté serveur).
export interface SaisirManche {
  tournoi_id: number
  phase_id: number
  match_numero: number
  numero: number
  valeurs_haut: string[]
  valeurs_bas: string[]
  identifiant_saisie: string
}

export interface SaisirBarrage {
  tournoi_id: number
  phase_id: number
  match_numero: number
  fleche_haut: string
  fleche_bas: string
  gagnant_designe: Cote | null
  identifiant_saisie: string
}

export interface ValiderDuel {
  tournoi_id: number
  phase_id: number
  match_numero: number
  identifiant_saisie: string
}

// --- Lectures ---

// Phases **d'un créneau** : lecture **publique** (aucune garde serveur), lue **sans jeton** par le
// scoreur. C'est bien `/departs/{id}/phases` — l'avancement —, pas `/tournois/{id}/phases`, qui rend
// le déroulé et dont les `id` appartiennent à une autre table (cf. `Phase` ci-dessus).
export function getPhases(departId: number): Promise<Phase[]> {
  return fetchJson<Phase[]>(`/api/v1/departs/${departId}/phases`, undefined, 'aucune')
}

export function getTableau(tournoiId: number, phaseId: number): Promise<Tableau> {
  return fetchJson<Tableau>(`/api/v1/duels/tableau/${tournoiId}/${phaseId}`, undefined, 'scoreur')
}

export function getDuel(tournoiId: number, phaseId: number, matchNumero: number): Promise<Duel> {
  return fetchJson<Duel>(
    `/api/v1/duels/duels/${tournoiId}/${phaseId}/${matchNumero}`,
    undefined,
    'scoreur',
  )
}

// --- Écritures (jeton X-Jeton-Scoreur ; routées par la file d'écriture serveur) ---
//
// ⚠️ **Deux familles de routes, un seul pavé** (E05US023, ADR-0083 §7). Une rencontre de poule est
// un duel ordinaire : même agrégat, même table `duel`, même écran de saisie. Ce qui diffère est la
// **navigation**, donc la ressource : `/api/v1/poules/...` au lieu de `/api/v1/duels/...`. Les
// corps sont identiques au nom du numéro près — le serveur appelle `numero` ce que le tableau
// appelle `match_numero`, et `manche` ce qu'il appelle `numero` —, d'où la traduction ci-dessous
// plutôt qu'un second jeu de types côté client.

const ROUTES: Record<FamilleDuel, { manches: string; barrages: string; validations: string }> = {
  tableau: {
    manches: '/api/v1/duels/manches',
    barrages: '/api/v1/duels/barrages',
    validations: '/api/v1/duels/validations',
  },
  poule: {
    manches: '/api/v1/poules/manches',
    barrages: '/api/v1/poules/barrages',
    validations: '/api/v1/poules/validations',
  },
}

// La réponse d'une route de poule enveloppe le duel dans sa rencontre (numéro, poule, tour,
// couloirs). Le pavé ne consomme que le duel : on déballe ici, une fois, plutôt que de rendre le
// type de retour des trois hooks dépendant de la famille.
interface RencontreEnveloppe {
  duel: Duel
}

function corpsPoule(corps: { match_numero: number }): Record<string, unknown> {
  const { match_numero, ...reste } = corps as { match_numero: number } & Record<string, unknown>
  return { ...reste, numero: match_numero }
}

async function ecrire(
  famille: FamilleDuel,
  acte: 'manches' | 'barrages' | 'validations',
  corps: { match_numero: number },
): Promise<Duel> {
  const chemin = ROUTES[famille][acte]
  if (famille === 'tableau') {
    return fetchJson<Duel>(chemin, { method: 'POST', body: JSON.stringify(corps) }, 'scoreur')
  }
  const enveloppe = await fetchJson<RencontreEnveloppe>(
    chemin,
    { method: 'POST', body: JSON.stringify(corpsPoule(corps)) },
    'scoreur',
  )
  return enveloppe.duel
}

export function saisirManche(corps: SaisirManche, famille: FamilleDuel = 'tableau'): Promise<Duel> {
  // Le rang de manche s'appelle `numero` côté tableau et `manche` côté poule : la traduction est
  // ici, pas dans le composant, pour que le pavé ne connaisse qu'une seule forme.
  if (famille === 'poule') {
    const { numero, ...reste } = corps
    return ecrire(famille, 'manches', { ...reste, manche: numero } as unknown as {
      match_numero: number
    })
  }
  return ecrire(famille, 'manches', corps)
}

export function saisirBarrage(
  corps: SaisirBarrage,
  famille: FamilleDuel = 'tableau',
): Promise<Duel> {
  return ecrire(famille, 'barrages', corps)
}

export function validerDuel(corps: ValiderDuel, famille: FamilleDuel = 'tableau'): Promise<Duel> {
  return ecrire(famille, 'validations', corps)
}
