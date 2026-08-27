// Le **modèle** des arrêts programmés (E05US033, ADR-0091) — logique pure.
//
// Séparé du composant pour la raison habituelle : `react-refresh` interdit à un module de rendu
// d'exporter aussi des fonctions, et la conversion « écran ↔ serveur » se teste ici sans DOM. ⚠️
// **Aucun miroir de règle serveur ici**, à la différence de `suisse.ts` : la validité d'un arrêt
// dépend du **nombre de tours**, que seul le serveur connaît (il varie avec l'effectif et la
// projection). Ce module ne juge que ce qui se juge sans rien savoir — un entier positif, pas deux
// arrêts au même endroit ; le reste est un refus serveur (422), le seul verdict honnête.

/** La portée d'un arrêt, miroir de `PorteeArret` (domaine). */
export type PorteeArret = 'phase' | 'depart'

/** Un arrêt tel que l'API le transporte, miroir de `ArretProgrammeDTO`. */
export interface ArretProgramme {
  apres_tour: number
  portee: PorteeArret
}

/** Une ligne d'arrêt telle que l'organisateur la saisit — la forme **éditable**.
 *
 * `apresTour` reste une **chaîne** : un champ vidé doit pouvoir rester vide pendant qu'on le
 * retape. ⚠️ `cle` est une identité **d'affichage**, jamais envoyée : sans elle React réutiliserait
 * les lignes par index, et supprimer la première ferait glisser la valeur de la deuxième dans son
 * champ — l'organisateur verrait son planning se réécrire sous ses doigts.
 */
export interface LigneArret {
  cle: string
  apresTour: string
  portee: PorteeArret
}

/** Ce que l'organisateur a choisi à l'écran, pour une étape donnée. */
export interface EtatArrets {
  lignes: LigneArret[]
}

/** Le plafond accepté par l'API (`ArretProgrammeDTO.apres_tour`, `le=64`). */
export const TOURS_MAX_REGLABLES = 64

/** L'état de départ : aucun arrêt — l'enchaînement automatique d'un tour au suivant, le défaut. */
export const ARRETS_PAR_DEFAUT: EtatArrets = { lignes: [] }

/** Fabrique une clé d'affichage pour une ligne neuve.
 *
 * ⚠️ **Un compteur, pas `Date.now()` ni `Math.random()`** : deux lignes ajoutées dans la même
 * milliseconde partageraient leur clé, et le rendu deviendrait indéterministe — exactement le
 * défaut que la clé existe pour éviter. Le compteur est local au module, ce qui suffit : les clés
 * ne franchissent jamais la frontière réseau.
 */
let compteur = 0
export function cleNeuve(): string {
  compteur += 1
  return `arret-${compteur}`
}

/** Une ligne neuve, prête à saisir : portée « cette phase seule », le geste le moins intrusif. */
export function ligneNeuve(): LigneArret {
  return { cle: cleNeuve(), apresTour: '', portee: 'phase' }
}

/** Reconstruit l'état d'édition depuis ce que porte l'étape. */
export function depuisEtape(arrets: ArretProgramme[] | null | undefined): EtatArrets {
  return {
    lignes: (arrets ?? []).map((arret) => ({
      cle: cleNeuve(),
      apresTour: String(arret.apres_tour),
      portee: arret.portee,
    })),
  }
}

function versEntier(brut: string): number | undefined {
  const nombre = Number(brut)
  if (brut.trim() === '' || !Number.isInteger(nombre)) return undefined
  if (nombre < 1 || nombre > TOURS_MAX_REGLABLES) return undefined
  return nombre
}

/**
 * Ce qui part au serveur pour les arrêts — `undefined` quand une ligne n'est pas exploitable.
 *
 * Même convention que les autres réglages : `undefined` veut dire « illisible », **pas** « efface ».
 * Une liste vide, elle, veut bien dire « aucun arrêt » et s'envoie telle quelle.
 */
export function versArrets(etat: EtatArrets): ArretProgramme[] | undefined {
  const arrets: ArretProgramme[] = []
  for (const ligne of etat.lignes) {
    const apresTour = versEntier(ligne.apresTour)
    if (apresTour === undefined) return undefined
    arrets.push({ apres_tour: apresTour, portee: ligne.portee })
  }
  return arrets
}

/**
 * Les tours sur lesquels **plusieurs** arrêts sont posés — vide si tout va bien.
 *
 * Le serveur refuse déjà ce cas (`ArretProgrammeInvalide`, 422), et c'est lui qui fait autorité. Le
 * dire à l'écran n'est donc pas une seconde règle mais un **service rendu** : l'organisateur qui a
 * saisi deux fois « après le tour 3 » voit lequel corriger, plutôt qu'un refus global à la
 * soumission.
 */
export function toursEnDoublon(etat: EtatArrets): number[] {
  const vus = new Map<number, number>()
  for (const ligne of etat.lignes) {
    const tour = versEntier(ligne.apresTour)
    if (tour === undefined) continue
    vus.set(tour, (vus.get(tour) ?? 0) + 1)
  }
  return [...vus.entries()]
    .filter(([, nombre]) => nombre > 1)
    .map(([tour]) => tour)
    .sort((a, b) => a - b)
}

/** Vrai si l'état est soumettable : chaque ligne lisible et aucun doublon. */
export function estValide(etat: EtatArrets): boolean {
  if (versArrets(etat) === undefined) return false
  return toursEnDoublon(etat).length === 0
}

/**
 * La phrase qui décrit ce qu'un arrêt va faire, en français de salle.
 *
 * L'écran ne peut pas dire *quand* l'arrêt tombera (il ignore le nombre de tours et l'heure), mais il
 * peut dire **ce qu'il coupera** — et c'est la seule chose que l'organisateur ait besoin de relire
 * pour vérifier son planning.
 */
export function decrire(ligne: LigneArret): string {
  const tour = versEntier(ligne.apresTour)
  if (tour === undefined) return 'Indiquez après quel tour la salle s’arrête.'
  if (ligne.portee === 'phase') {
    return `À la fin du tour ${tour}, cette phase se met en pause. Les autres continuent.`
  }
  return (
    `À la fin du tour ${tour}, tout le créneau se met en pause — ` +
    'chaque phase finissant d’abord le tour qu’elle a en cours.'
  )
}
