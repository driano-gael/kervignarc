// Présentation des tableaux de duels (E07US005) — logique pure, testée en node (comme les autres
// `presentation.ts` des features). Rien ici ne dépend de React : c'est la règle de lecture d'un
// arbre, et elle doit pouvoir échouer dans un test plutôt que sur un écran projeté.
//
// Deux lectures, celles de la maquette P05 :
//
//  - **A · « Mon chemin »** (`cheminDeArcher`) — recommandée : l'arbre réduit à la trajectoire d'un
//    archer suivi. « L'archer est le sujet, la compétition est le contexte » (`D-09`).
//  - **B · « Arbre complet »** (`parTour`) — nécessaire en second : l'arbre en vraies branches ne
//    tient pas sur 360 px, en **liste par tour** si. C'est la concession mobile assumée par la
//    maquette, pas un pis-aller.
//
// ⚠️ Le fil rouge de ce fichier : **ne jamais affirmer plus que ce que le serveur sait**. Trois
// pièges, chacun verrouillé par un test :
//  1. un duel **tiré mais pas validé** n'a pas de vainqueur acquis — l'arbre ne rejoue que le
//     validé, donc annoncer « gagné » promettrait une qualification que la ligne suivante dément ;
//  2. un archer **battu n'est pas forcément éliminé** — depuis E06US006, la profondeur intégrale
//     le fait descendre dans un tableau de placement où il tire encore ;
//  3. un **exempt n'est pas une victoire** — il n'y avait personne en face, et aucun score à
//     chercher.

import type { DuelPublic, DuellistePublic, TableauPublic } from './api'

/** Le camp d'un duelliste dans un match. Miroir de `domain.duel.Cote`. */
export type Cote = 'haut' | 'bas'

/** Où en est l'archer sur une étape de son chemin.
 *
 * `en_attente` est le statut qui manque partout ailleurs et sans lequel la vue ment : le duel est
 * allé au bout, le scoreur n'a pas encore scellé. `a_venir` est une étape **sans match** — un tour
 * que l'arbre porte encore et que l'archer peut atteindre.
 */
export type StatutEtape =
  'gagne' | 'perdu' | 'en_attente' | 'a_jouer' | 'attente_adversaire' | 'exempt' | 'a_venir'

export interface EtapeChemin {
  tour: number
  libelle: string
  /** L'enjeu nommé (« Finale », « Places 5 à 8 »), ou `null` si le tableau n'en met pas. */
  enjeu: string | null
  adversaire: DuellistePublic | null
  statut: StatutEtape
  /** Le score **vu de l'archer suivi** (« 6 — 2 »), ou `null` si rien n'est tiré. */
  score: string | null
}

export interface GroupeDeTour {
  tour: number
  libelle: string
  duels: DuelPublic[]
}

/** Le nom du tour, tel que la salle le dit — pas « tour 3 sur 3 » (règle 3, vocabulaire FFTA).
 *
 * Se calcule sur le **nombre de tours restants**, pas sur le rang du tour : c'est ce qui rend le
 * libellé juste quel que soit l'effectif. Au-delà des quarts, la langue n'a plus de mot et l'on
 * bascule sur les fractions imprimées sur les tableaux papier de la fédération.
 */
export function libelleTour(tour: number, nbTours: number): string {
  const restants = 2 ** (nbTours - tour + 1)
  if (restants <= 2) return 'Finale'
  if (restants === 4) return 'Demi-finales'
  if (restants === 8) return 'Quarts de finale'
  return `1/${restants / 2} de finale`
}

/** L'enjeu d'un match, nommé depuis la **place en jeu** et jamais déduit du tour.
 *
 * La déduction par le tour serait fausse dès qu'un tableau descend sous le podium (E06US006) : le
 * match des places 5-8 se joue au **même tour** que la demi-finale, et l'appeler « demi-finale »
 * ferait chercher un podium à qui n'en jouera pas.
 */
export function libelleEnjeu(place: number[] | null): string | null {
  // `noUncheckedIndexedAccess` : un tuple venu du réseau n'est qu'un tableau, ses cases sont
  // `number | undefined`. On les extrait explicitement plutôt que de rassurer TS par un cast —
  // le DTO promet deux entiers, la promesse d'un DTO n'est pas une garantie d'exécution.
  const debut = place?.[0]
  const fin = place?.[1]
  if (debut === undefined || fin === undefined) return null
  if (debut === 1 && fin === 2) return 'Finale'
  if (debut === 3 && fin === 4) return 'Petite finale'
  // Une plage large (« 5 à 8 ») décrit un sous-tableau encore ouvert ; une plage serrée (« 5-6 »)
  // décrit le match qui départage. Deux mots différents pour deux situations différentes.
  return fin - debut === 1 ? `Places ${debut}-${fin}` : `Places ${debut} à ${fin}`
}

/** Le score de sets **du point de vue d'un camp** — l'archer suivi est toujours à gauche. */
export function scoreVu(duel: DuelPublic, cote: Cote): string | null {
  if (duel.points_haut === null || duel.points_bas === null) return null
  return cote === 'haut'
    ? `${duel.points_haut} — ${duel.points_bas}`
    : `${duel.points_bas} — ${duel.points_haut}`
}

/** Le camp occupé par un archer dans un match, ou `null` s'il n'y est pas. */
function coteDe(duel: DuelPublic, archerId: number): Cote | null {
  if (duel.haut?.archer_id === archerId) return 'haut'
  if (duel.bas?.archer_id === archerId) return 'bas'
  return null
}

function statutDeLEtape(duel: DuelPublic, cote: Cote, adversaire: DuellistePublic | null) {
  if (duel.est_bye) return 'exempt' as const
  // Piège n°1 : `validee`, pas `termine`. Tant que le scoreur n'a pas scellé, l'arbre n'a pas
  // avancé et le résultat n'est pas acquis.
  if (duel.validee && duel.vainqueur !== null) {
    return duel.vainqueur === cote ? ('gagne' as const) : ('perdu' as const)
  }
  if (duel.termine) return 'en_attente' as const
  return adversaire === null ? ('attente_adversaire' as const) : ('a_jouer' as const)
}

/** Le chemin d'un archer dans un tableau : ses matchs, puis les tours qu'il peut encore atteindre.
 *
 * Les matchs viennent du serveur, qui les tient à jour tout seul — un vainqueur validé occupe
 * **déjà** son match du tour suivant, et un perdant que la cascade repêche occupe **déjà** le sien
 * dans le tableau de placement. Il n'y a donc rien à deviner : parcourir les matchs qui portent
 * l'archer suffit, et c'est ce qui rend le piège n°2 impossible.
 *
 * Les étapes `a_venir` ne sont ajoutées que si la dernière étape connue **laisse une suite
 * ouverte** : un archer battu et non repêché s'arrête sur sa défaite, sans qu'on ait besoin de
 * savoir si le tableau le repêche — c'est l'absence de match ultérieur qui le dit, pas une règle
 * de format recopiée ici (elle vit dans `routing`, règle 2).
 */
export function cheminDeArcher(tableau: TableauPublic, archerId: number): EtapeChemin[] {
  const siens = tableau.duels
    .map((duel) => ({ duel, cote: coteDe(duel, archerId) }))
    .filter((x): x is { duel: DuelPublic; cote: Cote } => x.cote !== null)
    .sort((a, b) => a.duel.tour - b.duel.tour)
  if (siens.length === 0) return []

  const etapes: EtapeChemin[] = siens.map(({ duel, cote }) => {
    const adversaire = cote === 'haut' ? duel.bas : duel.haut
    return {
      tour: duel.tour,
      libelle: libelleTour(duel.tour, tableau.nb_tours),
      enjeu: libelleEnjeu(duel.place_en_jeu),
      adversaire,
      statut: statutDeLEtape(duel, cote, adversaire),
      score: scoreVu(duel, cote),
    }
  })

  const derniere = etapes[etapes.length - 1]
  if (derniere === undefined) return etapes
  const sorti = derniere.statut === 'perdu'
  for (let tour = derniere.tour + 1; !sorti && tour <= tableau.nb_tours; tour += 1) {
    etapes.push({
      tour,
      libelle: libelleTour(tour, tableau.nb_tours),
      enjeu: null,
      adversaire: null,
      statut: 'a_venir',
      score: null,
    })
  }
  return etapes
}

/** L'arbre complet en **liste par tour** — variante B de la maquette.
 *
 * Les **exempts sont écartés** : un bye occupe une place de l'arbre mais ne se tire pas, et le
 * lister ferait chercher une rencontre qui n'aura pas lieu. Même filtre que le suivi du déroulé
 * (E07US004), pour la même raison.
 */
export function parTour(tableau: TableauPublic): GroupeDeTour[] {
  const groupes = new Map<number, DuelPublic[]>()
  for (const duel of tableau.duels) {
    if (duel.est_bye) continue
    const existant = groupes.get(duel.tour)
    if (existant === undefined) groupes.set(duel.tour, [duel])
    else existant.push(duel)
  }
  return [...groupes.entries()]
    .sort(([a], [b]) => a - b)
    .map(([tour, duels]) => ({
      tour,
      libelle: libelleTour(tour, tableau.nb_tours),
      duels: [...duels].sort((a, b) => a.numero - b.numero),
    }))
}
