// Les trois axes de travail de l'admin et la lecture de l'adresse (E14US003, ADR-0058, ADR-0059).
//
// Séparé de `CoquilleAdmin.tsx` pour deux raisons : la règle ESLint `react-refresh/only-export-components`
// (un `.tsx` n'exporte que des composants — même parti que `features/poste/url.ts`), et parce que ces
// fonctions sont **pures**, donc testables sans rendu. C'est là que vivent les décisions ; la coquille
// n'en fait que l'affichage.

import type { DestinationAdminId } from './aide-ecrans'
// Import **de type seulement** : `axes.ts` reste pur et sans dépendance d'exécution vers une autre
// feature. Le statut est une union fermée — le typer `string` laissait une faute de frappe cesser
// silencieusement de matcher (relevé à la revue).
import type { Tournoi } from '../competition/api'

// `besoinTournoi` dit si l'axe travaille **sur un tournoi**. L'atelier, non : c'est le patrimoine du
// club, il vit d'année en année — d'où l'absence de sélecteur de tournoi dans cet axe.
export type Axe = 'atelier' | 'pilotage' | 'gestion'

// **L'ordre a changé au retour maquettes du 04/08/2026** (A02) : *« la ligne de déroulé doit être la
// première »*, *« mettre la section déroulé un peu plus en avant »*.
//
// Ce n'est pas une préférence d'affichage : l'accueil de l'admin est ce qu'on voit **le matin du jour
// J**, l'écran devant lequel on est quand quelque chose se joue vraiment. L'atelier venait en tête
// par héritage — il était le premier axe fabriqué, pas le premier à servir. Le pilotage est
// désormais l'axe d'ouverture, l'atelier passe en dernier : on ne fabrique pas de briques pendant
// qu'un tournoi tourne.
export const AXES: { axe: Axe; libelle: string; phrase: string; besoinTournoi: boolean }[] = [
  {
    axe: 'pilotage',
    libelle: 'Pilotage',
    phrase: 'Le temps réel : lancer, superviser, valider, faire tourner la journée.',
    besoinTournoi: true,
  },
  {
    axe: 'gestion',
    libelle: 'Gestion',
    phrase: 'L’administratif : inscriptions, paiements, exports, archives.',
    besoinTournoi: true,
  },
  {
    axe: 'atelier',
    libelle: 'Atelier',
    phrase: 'Fabriquer : briques du club, salles types, formats de déroulé, banc d’essai.',
    besoinTournoi: false,
  },
]

/** L'axe de chaque destination livrée — **source unique** de la répartition.
 *
 * Le `Record<Exclude<DestinationAdminId, 'tournoi'>, Axe>` est **exhaustif** : oublier une
 * destination ne compile plus. C'est ce qui remplace les 24 champs `axe:` recopiés à la main dans
 * `CoquilleAdmin`, où une entrée mal étiquetée disparaissait **silencieusement** de la sidebar.
 * `tournoi` est absente **exprès** : c'est l'**assemblage**, porté par l'accueil (ADR-0058).
 */
export const AXE_PAR_DESTINATION: Record<Exclude<DestinationAdminId, 'tournoi'>, Axe> = {
  // Atelier — fabriquer, hors tournoi. Depuis E01US023, ses destinations le sont
  // réellement (clubs, gabarits, catégories, blasons, formats, déroulé, jeu d'essai) :
  // catégories, blasons et formats sont devenus des briques du **club** (ADR-0060), et `bareme` /
  // `phases` — qui règlent **une** édition — sont partis au pilotage, exactement comme `plan` (la
  // copie d'un tournoi) est au pilotage tandis que `gabarits` (le modèle) est ici.
  clubs: 'atelier',
  gabarits: 'atelier',
  categories: 'atelier',
  blasons: 'atelier',
  formats: 'atelier',
  deroule: 'atelier',
  'jeu-essai': 'atelier',
  // Pilotage — le temps réel, et ce qui règle **cette** édition.
  accueil: 'pilotage',
  assemblage: 'pilotage',
  bareme: 'pilotage',
  phases: 'pilotage',
  // L'identité règle **cette** édition (un logo d'événement change à chaque année), pas le
  // patrimoine du club : elle est au pilotage comme `bareme` et `phases`, et non à l'atelier —
  // qui n'a pas de sélecteur de tournoi.
  identite: 'pilotage',
  // `simulation` **rejoue le tournoi courant** : elle exige donc une édition, exactement comme
  // `bareme` et `phases`. La laisser à l'atelier rouvrait l'impasse de DETTE-023 — « choisissez un
  // tournoi ci-dessus » sur un axe qui n'a pas de sélecteur (relevé par trois axes de revue).
  simulation: 'pilotage',
  supervision: 'pilotage',
  ecrans: 'pilotage',
  'suivi-deroule': 'pilotage',
  'feu-vert': 'pilotage',
  // Les deux membres livrés de la famille « prêt à… » (E16US012) sont **voisins** dans la
  // sidebar : c'est leur adjacence qui les fait lire comme une famille plutôt que comme deux
  // écrans qui se ressemblent.
  'pret-demarrer': 'pilotage',
  completude: 'pilotage',
  classement: 'pilotage',
  // Le palmarès se **consulte** pendant que le tournoi tourne (les podiums se remplissent au fil
  // des duels) : pilotage, comme le classement en direct — et non gestion, où il ne serait
  // regardé qu'une fois tout fini.
  palmares: 'pilotage',
  postes: 'pilotage',
  scoreurs: 'pilotage',
  plan: 'pilotage',
  placement: 'pilotage',
  duels: 'pilotage',
  departs: 'pilotage',
  // Gestion — l'administratif, transverse au temps.
  inscriptions: 'gestion',
  paiements: 'gestion',
  exports: 'gestion',
  archive: 'gestion',
}

/** Quelles destinations exigent un **tournoi courant** — ce que `CoquilleAdmin` consomme pour
 * choisir entre l'écran et « choisissez un tournoi ».
 *
 * Elle vivait dans un tableau local, donc **hors de portée des tests** : le garde-fou ne pouvait
 * pas vérifier l'invariant qu'il annonçait et se rabattait sur des appartenances d'axe. Ici,
 * l'invariant est **prouvable**, et le `Record` exhaustif force toute destination neuve à répondre.
 */
export const BESOIN_TOURNOI: Record<Exclude<DestinationAdminId, 'tournoi'>, boolean> = {
  // Atelier — le patrimoine du club, aucune édition requise.
  clubs: false,
  gabarits: false,
  categories: false,
  blasons: false,
  formats: false,
  deroule: false,
  'jeu-essai': false,
  // Pilotage & gestion — tout y porte sur une édition précise.
  accueil: true,
  assemblage: true,
  bareme: true,
  identite: true,
  phases: true,
  simulation: true,
  supervision: true,
  ecrans: true,
  'suivi-deroule': true,
  'feu-vert': true,
  'pret-demarrer': true,
  completude: true,
  classement: true,
  palmares: true,
  postes: true,
  scoreurs: true,
  plan: true,
  placement: true,
  duels: true,
  departs: true,
  inscriptions: true,
  paiements: true,
  exports: true,
  archive: true,
}

/** Destination d'ouverture d'un axe.
 *
 * Pilotage : l'**accueil-tableau de bord** (`D-20`), qui se contextualise par statut. Atelier :
 * **`formats`** depuis E01US025 — c'est de lui que découle un tournoi concret, ouvrir ailleurs
 * ferait entrer par un composant. C'était `gabarits` tant que quatre destinations exigeaient un
 * tournoi que l'axe ne propose pas de choisir : le premier clic affichait « choisissez un tournoi
 * **ci-dessus** » sans rien au-dessus (DETTE-023, résorbée).
 */
export function destinationParDefaut(axe: Axe): DestinationAdminId {
  if (axe === 'pilotage') return 'accueil'
  if (axe === 'gestion') return 'inscriptions'
  return 'formats'
}

// Lecture et écriture de l'adresse admin : `/admin/<tournoi?>/<axe?>/<destination?>/<élément?>`.
//
// Le **tournoi est dans l'adresse** (E14US003) : sans lui, un `F5` ou un lien partagé restaurait
// l'écran mais pas son sujet, et 21 des 24 destinations en dépendent. Il est placé **avant** l'axe
// pour survivre au changement d'axe et se lire dans l'ordre naturel. Il est reconnu par sa
// **forme** (suite de chiffres) : aucun axe ni aucune destination n'est numérique.

// Le 4ᵉ segment — **l'élément que la destination ouvre** — vient d'E16US010 (ADR-0100) : un
// résultat de recherche doit pouvoir dire « ouvre la fiche de l'archer 57 », et l'état d'ouverture
// vivait en `useState` local à la ligne, hors d'atteinte. ⚠️ Il est **numérique** lui aussi, mais
// sans ambiguïté avec le tournoi : celui-ci est en tête, l'élément en 4ᵉ position.

export interface RouteAdmin {
  tournoiId: number | null
  axe: Axe | null
  destinationDemandee: string | null
  /** L'élément que la destination doit ouvrir, ou `null` — voir ADR-0100. */
  elementDemande: number | null
}

function estIdentifiant(segment: string | undefined): segment is string {
  return segment !== undefined && /^\d+$/.test(segment)
}

// Le mot qui dit « ouvre-la » sur l'accueil. `/admin/12` désigne le tournoi courant ; `/admin/12/
// fiche` demande en plus d'ouvrir son formulaire. Non numérique, donc jamais confondu avec un axe.
const SEGMENT_FICHE = 'fiche'

/**
 * L'élément que l'écran doit **ouvrir** — deux formes d'adresse, un seul sens (ADR-0100).
 *
 * Sous une destination, c'est le 4ᵉ segment. Sur l'accueil — qui n'a ni axe ni destination et où
 * vit la liste des tournois — l'élément **est** le tournoi courant, d'où `SEGMENT_FICHE`.
 * ⚠️ Sans écran pour l'ouvrir, l'adresse porterait un état que rien ne consomme.
 */
function elementOuvert(
  tournoiId: number | null,
  axe: Axe | null,
  destination: string | null,
  premier: string | undefined,
  quatrieme: string | undefined,
): number | null {
  if (axe === null) return premier === SEGMENT_FICHE ? tournoiId : null
  return destination !== null && estIdentifiant(quatrieme) ? Number(quatrieme) : null
}

/** Traduit les segments qui suivent `/admin` en route d'administration. */
export function analyserSegmentsAdmin(segments: readonly string[]): RouteAdmin {
  const reste = [...segments]
  const tournoiId = estIdentifiant(reste[0]) ? Number(reste.shift()) : null
  const [premier, second, troisieme] = reste
  const axe = AXES.find((a) => a.axe === premier)?.axe ?? null
  const destinationDemandee = axe === null ? null : (second ?? null)
  return {
    tournoiId,
    axe,
    destinationDemandee,
    elementDemande: elementOuvert(tournoiId, axe, destinationDemandee, premier, troisieme),
  }
}

/** Construit les segments d'une adresse d'administration. Réciproque d'`analyserSegmentsAdmin`. */
export function segmentsAdmin(
  tournoiId: number | null,
  axe: Axe | null,
  destination: DestinationAdminId | null,
  element: number | null = null,
): string[] {
  const segments: string[] = []
  if (tournoiId !== null) segments.push(String(tournoiId))
  // Accueil : l'élément **est** le tournoi, on ne le répète pas — on demande son ouverture.
  if (axe === null) {
    if (tournoiId !== null && element === tournoiId) segments.push(SEGMENT_FICHE)
    return segments
  }
  segments.push(axe)
  if (destination !== null) segments.push(destination)
  if (destination !== null && element !== null) segments.push(String(element))
  return segments
}

/**
 * La destination demandée, **validée contre celles que l'axe propose réellement**.
 *
 * Sans cette validation, `/admin/atelier/supervision` afficherait un écran de pilotage sous
 * l'intitulé « Atelier » — exactement le mélange que le découpage supprime.
 */
export function destinationValide(
  demandee: string | null,
  destinationsDeLAxe: readonly DestinationAdminId[],
): DestinationAdminId | null {
  return destinationsDeLAxe.find((d) => d === demandee) ?? null
}

/** Ce sur quoi l'axe **Pilotage** travaille en ce moment — la ligne de contexte d'A02 (E17US003).
 *
 * Pure et sortie du composant pour être **testable** : deux règles ne se voient pas dans le rendu —
 * un tournoi **en pause** compte comme en cours, et « aucun tournoi en cours » rend `null` plutôt
 * qu'une chaîne vide. La planche montre aussi le départ courant et « 28/30 postes en ligne » : non
 * repris, ce sont des agrégats que le serveur n'expose pas (écart inscrit au relevé d'EPIC-17).
 */
export function tournoisEnCours<T extends { statut: Tournoi['statut'] }>(
  tournois: readonly T[],
): readonly T[] {
  // « En pause » compte : le tournoi est **lancé**, il attend. La règle vit ici et nulle part
  // ailleurs — la dupliquer dans le composant, c'est se donner deux définitions qui divergeront.
  return tournois.filter((t) => t.statut === 'en_cours' || t.statut === 'en_pause')
}

export function contextePilotage(
  tournois: readonly Pick<Tournoi, 'nom' | 'statut'>[],
): string | null {
  const enCours = tournoisEnCours(tournois)
  return enCours.length === 0 ? null : enCours.map((t) => t.nom).join(' · ')
}
