// Présentation des tableaux de duels (E07US005) — logique pure, testée en node. Deux lectures
// (maquette P05) : « Mon chemin » (`cheminDeArcher`), l'arbre réduit à un archer suivi, et « Arbre
// complet » (`parTour`), en **liste par branche** faute de tenir sur 360 px. ⚠️ **Aucun nom de
// match n'est calculé ici** : nommer un match est du vocabulaire métier (règle 3), servi par
// `DuelPublic.libelle` — recalculé en TS, il affichait « Demi-finales » sur un match des places 5-8
// (`DETTE-020` compte déjà deux domiciles). Fil rouge : **ne jamais affirmer plus que ce que le
// serveur sait** — tiré ≠ validé, battu ≠ éliminé, exempt ≠ victoire.

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
  /** Le nom du match, **tel que le serveur le donne** — ou `null` sur une étape à venir dont la
   * branche n'est pas encore décidée. Un `null` s'affiche « À venir » : ne rien nommer vaut
   * infiniment mieux que nommer faux. */
  libelle: string | null
  adversaire: DuellistePublic | null
  statut: StatutEtape
  /** Le score **vu de l'archer suivi** (« 6 — 2 »), ou `null` si rien n'est tiré. */
  score: string | null
}

/** Ce qu'on écrit en face de chaque étape d'un chemin. **Un mot par situation, jamais une couleur
 * seule** (`DV-03`) : l'écran de salle est vu de loin et l'appli publique est lue en plein soleil.
 *
 * Vit ici et non dans un composant depuis E16US004 : deux écrans le lisent désormais (l'arbre
 * « Mon chemin » et le récapitulatif de journée de la carte de suivi), et un vocabulaire dupliqué
 * finit par diverger — c'est ce que `DETTE-020` compte déjà deux fois sur cette feature. */
export const LIBELLE_STATUT: Record<StatutEtape, string> = {
  gagne: 'Gagné',
  perdu: 'Perdu',
  en_attente: 'En attente de validation',
  a_jouer: 'À tirer',
  attente_adversaire: 'Adversaire à désigner',
  exempt: 'Exempt',
  a_venir: 'À venir',
}

export interface GroupeDeBranche {
  /** Clé de regroupement : le libellé du serveur. Deux branches partageant un tour (une demi-finale
   * et un match des places 5-8) forment donc **deux groupes**, pas un seul. */
  libelle: string
  tour: number
  duels: DuelPublic[]
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

/** Une branche est-elle **incluse** dans une autre ? Les plages se divisent en deux à chaque tour,
 * donc la branche d'un tour suivant est toujours une sous-plage de la branche courante. */
function inclus(interne: number[] | null, externe: number[] | null): boolean {
  if (externe === null || interne === null) return true
  const [db, fb] = [externe[0], externe[1]]
  const [di, fi] = [interne[0], interne[1]]
  if (db === undefined || fb === undefined || di === undefined || fi === undefined) return true
  return di >= db && fi <= fb
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

/** Le nom d'un tour que l'archer n'a pas encore atteint — **lu** sur les matchs réels, jamais
 * calculé (le vocabulaire n'a qu'un domicile, le domaine).
 *
 * On rend **les noms possibles** : un seul s'il n'y a qu'une suite, les deux joints sinon. ⚠️ Un
 * premier correctif rendait `null` dès que plusieurs noms coexistaient, en présentant ce cas comme
 * l'exception : c'était **la règle** — sous profondeur podium la dernière ligne n'était jamais
 * nommée. Au-delà de deux noms on ne nomme plus : quatre libellés encombrent au lieu d'informer.
 */
const MAX_NOMS_JOINTS = 2

function libelleDuTourAVenir(
  tableau: TableauPublic,
  tour: number,
  branche: number[] | null,
): string | null {
  const noms = [
    ...new Set(
      tableau.duels
        .filter((d) => d.tour === tour && inclus(d.plage, branche))
        .map((d) => d.libelle),
    ),
  ]
  if (noms.length === 0 || noms.length > MAX_NOMS_JOINTS) return null
  return noms.join(' ou ')
}

/** Le chemin d'un archer dans un tableau : ses matchs, puis les tours qu'il peut encore atteindre.
 *
 * Les matchs viennent du serveur, qui les tient à jour — un vainqueur validé occupe **déjà** son
 * match suivant : il n'y a rien à deviner. ⚠️ Les étapes `a_venir` ne sont ajoutées que si la
 * dernière étape connue laisse une suite **acquise** (`gagne`, `exempt`, ou match à disputer) ; un
 * `perdu` ferme le parcours, et un **`en_attente` aussi** — tant que le scoreur n'a pas scellé, un
 * archer battu 6-0 lisait « Demi-finales · À venir » juste sous son score.
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
      libelle: duel.libelle,
      adversaire,
      statut: statutDeLEtape(duel, cote, adversaire),
      score: scoreVu(duel, cote),
    }
  })

  const dernier = siens[siens.length - 1]
  const derniere = etapes[etapes.length - 1]
  if (derniere === undefined || dernier === undefined) return etapes
  const suiteOuverte = derniere.statut !== 'perdu' && derniere.statut !== 'en_attente'
  for (let tour = derniere.tour + 1; suiteOuverte && tour <= tableau.nb_tours; tour += 1) {
    etapes.push({
      tour,
      libelle: libelleDuTourAVenir(tableau, tour, dernier.duel.plage),
      adversaire: null,
      statut: 'a_venir',
      score: null,
    })
  }
  return etapes
}

/** Ce qu'un archer a joué dans **une** phase : le tableau, et ses tours effectivement disputés. */
export interface ParcoursPhase {
  phaseId: number
  ordre: number
  /** Le type de phase, tel que le serveur le nomme (`TypePhase`). Le libellé se prend dans
   * `shared/phases/catalogue.ts` — domicile unique du vocabulaire (règle 3). */
  type: string
  etapes: EtapeChemin[]
}

/** Les étapes qui ont **eu lieu**. `a_jouer` et `attente_adversaire` décrivent un match qui n'est
 * pas tiré ; `a_venir` un tour que l'archer n'a même pas atteint. */
const ETAPES_JOUEES: ReadonlySet<StatutEtape> = new Set<StatutEtape>([
  'gagne',
  'perdu',
  'en_attente',
  'exempt',
])

/** Le récapitulatif de la journée d'un archer, **toutes phases confondues** (E16US004, P02).
 *
 * `cheminDeArcher` ne connaît qu'**un** tableau ; ici on parcourt tous ceux du créneau, dans
 * l'ordre des phases, en ne gardant que celles où l'archer a tiré. ⚠️ **Lecture rétrospective** :
 * les étapes `a_venir` sont écartées — ce qui reste à jouer est déjà porté par le bloc « Ensuite »
 * (E07US008), et deux réponses à la même question divergent, celle d'ici étant la moins bien
 * informée.
 */
export function parcoursToutesPhases(tableaux: TableauPublic[], archerId: number): ParcoursPhase[] {
  return [...tableaux]
    .sort((a, b) => a.ordre - b.ordre)
    .map((tableau) => ({
      phaseId: tableau.phase_id,
      ordre: tableau.ordre,
      type: tableau.type,
      etapes: cheminDeArcher(tableau, archerId).filter((e) => ETAPES_JOUEES.has(e.statut)),
    }))
    .filter((parcours) => parcours.etapes.length > 0)
}

/** L'arbre complet, groupé **par branche** — variante B de la maquette.
 *
 * ⚠️ **Par libellé, pas par numéro de tour** : grouper par tour brut range la petite finale sous «
 * Finale », et sous profondeur intégrale le bloc « Demi-finales » contenait aussi les places 5-8.
 * Le libellé du serveur distingue déjà ces branches. Deux filtres : les **exempts** (une place de
 * l'arbre qui ne se tire pas) et les matchs **sans aucun occupant** (à 9 h, l'écran projeté
 * affichait des suites de « — vs — »).
 */
export function parTour(tableau: TableauPublic): GroupeDeBranche[] {
  const groupes = new Map<string, GroupeDeBranche>()
  for (const duel of tableau.duels) {
    if (duel.est_bye) continue
    if (duel.haut === null && duel.bas === null) continue
    const existant = groupes.get(duel.libelle)
    if (existant === undefined) {
      groupes.set(duel.libelle, { libelle: duel.libelle, tour: duel.tour, duels: [duel] })
    } else {
      existant.duels.push(duel)
    }
  }
  return [...groupes.values()]
    .sort((a, b) => a.tour - b.tour || (a.duels[0]?.numero ?? 0) - (b.duels[0]?.numero ?? 0))
    .map((groupe) => ({ ...groupe, duels: [...groupe.duels].sort((a, b) => a.numero - b.numero) }))
}
