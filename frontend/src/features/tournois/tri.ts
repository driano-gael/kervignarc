// Ordre et filtrage de la liste des tournois — retour maquettes du 04/08/2026 (A02, A04).
//
// La liste était rendue dans l'ordre de création ; le commanditaire a demandé un ordre **métier** :
// statut (en cours, prêt, terminé, brouillon) puis date, « surtout si on est à la date prévue ».
// C'est une **règle**, pas de la mise en forme — elle décide ce que l'organisateur voit en premier
// le matin du jour J —, d'où un module pur, testable sans rendu. ⚠️ `aujourdhui` est un
// **paramètre**, jamais `new Date()` lu ici : une fonction qui lit l'horloge ne se teste pas de
// façon déterministe (règle 9).

import type { StatutTournoi, Tournoi } from '../competition/api'

/** Rang d'affichage de chaque statut. Les quatre premiers sont **dictés** par A04 ; les trois
 * autres sont déduits, et le raisonnement est écrit ici parce qu'il n'a pas été arbitré :
 * `en_pause` suit immédiatement `en_cours` (même tournoi, simplement interrompu — le reléguer plus
 * bas le ferait disparaître de la tête de liste au moment où l'on y revient) ; `archive` et
 * `annule` ferment la marche, seuls statuts sur lesquels il n'y a plus rien à faire.
 *
 * `Record` exhaustif : ajouter un huitième statut sans lui donner de rang ne compilera plus.
 */
export const RANG_STATUT: Record<StatutTournoi, number> = {
  en_cours: 0,
  en_pause: 1,
  pret: 2,
  termine: 3,
  brouillon: 4,
  archive: 5,
  annule: 6,
}

/** Les statuts sur lesquels il reste quelque chose à faire — ils se lisent du plus proche au plus
 * lointain. Les autres sont clos : on les lit du plus récent au plus ancien, parce que la question
 * qu'on leur pose est « celui de la semaine dernière », jamais « celui d'il y a trois ans ». */
const OUVERTS: readonly StatutTournoi[] = ['brouillon', 'pret', 'en_cours', 'en_pause']

/** La liste, dans l'ordre où l'organisateur veut la lire : par statut, puis par date.
 *
 * Le « surtout si on est à la date prévue » d'A02 n'ajoute **pas** un troisième critère : trier
 * les `pret` par date croissante fait déjà remonter celui du jour. Un critère « proximité à
 * aujourd'hui » aurait placé un tournoi d'hier avant un tournoi de demain. ⚠️ Tri **non
 * destructif** : on copie avant de trier, sinon on réordonnerait le cache React Query.
 */
export function ordonnerTournois(tournois: readonly Tournoi[]): Tournoi[] {
  return [...tournois].sort((a, b) => {
    const parStatut = RANG_STATUT[a.statut] - RANG_STATUT[b.statut]
    if (parStatut !== 0) return parStatut
    // Les dates sont en ISO `AAAA-MM-JJ` : l'ordre lexicographique **est** l'ordre chronologique.
    const chrono = a.date.localeCompare(b.date)
    return OUVERTS.includes(a.statut) ? chrono : -chrono
  })
}

/** Un tournoi qui se joue **aujourd'hui** — ce que le jour J doit sauter aux yeux (A02). */
export function estAujourdhui(tournoi: Tournoi, aujourdhui: string): boolean {
  return tournoi.date === aujourdhui
}

/** La date du jour au format ISO `AAAA-MM-JJ`, dans le fuseau **local**.
 *
 * `toISOString()` serait un piège : il convertit en UTC, donc en France un tournoi consulté avant
 * 01 h ou 02 h du matin (heure d'hiver / d'été) serait daté de la veille. Un tournoi commence à 8 h,
 * mais l'organisateur qui prépare sa salle à 23 h 30 la veille regarde bien « demain ».
 */
export function dateDuJour(maintenant: Date): string {
  const mois = String(maintenant.getMonth() + 1).padStart(2, '0')
  const jour = String(maintenant.getDate()).padStart(2, '0')
  return `${maintenant.getFullYear()}-${mois}-${jour}`
}

/** Les statuts réellement présents dans une liste, dans l'ordre d'affichage — de quoi ne proposer
 * que des filtres qui donnent un résultat, avec leur décompte. Un filtre « Annulé (0) » sur une base
 * qui n'en contient aucun n'apprend rien et occupe une place. */
export function statutsPresents(
  tournois: readonly Tournoi[],
): { statut: StatutTournoi; nombre: number }[] {
  const compte = new Map<StatutTournoi, number>()
  for (const t of tournois) compte.set(t.statut, (compte.get(t.statut) ?? 0) + 1)
  return [...compte.entries()]
    .map(([statut, nombre]) => ({ statut, nombre }))
    .sort((a, b) => RANG_STATUT[a.statut] - RANG_STATUT[b.statut])
}

/** Applique le filtre par statut. Un filtre **vide vaut « tout »** : c'est l'état d'ouverture de
 * l'écran, et il ne faut jamais qu'un clic malheureux laisse l'organisateur devant une liste vide
 * sans comprendre pourquoi. */
export function filtrerParStatut(
  tournois: readonly Tournoi[],
  retenus: ReadonlySet<StatutTournoi>,
): Tournoi[] {
  if (retenus.size === 0) return [...tournois]
  return tournois.filter((t) => retenus.has(t.statut))
}
