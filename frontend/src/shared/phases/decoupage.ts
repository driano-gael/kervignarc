// Le **modèle** du découpage d'une qualification en tours (E05US035, ADR-0093) — logique pure.
//
// Séparé du composant pour la raison habituelle (`suisse.ts`, `poules.ts`, `bigShootOff.ts`) :
// `react-refresh` interdit à un module de rendu d'exporter aussi des fonctions, et la conversion
// « ce que l'écran affiche ↔ ce qui part au serveur » se teste ici sans monter de DOM.
//
// ⚠️ **La divisibilité est un miroir assumé du domaine** (`domain/qualification.py::
// verifier_decoupage`), au même titre que `rondesMaximales` pour le suisse. Le serveur fait
// autorité — `EtapeDeroule` **refuse** un découpage qui ne tombe pas juste. Mais l'organisateur
// n'a aucune raison de découvrir la règle en se faisant refuser son étape : la dire à l'écran vaut
// mieux que la lui opposer. Sa dérive ne produirait qu'un avertissement faux, jamais un tournoi
// faux.

/** Le réglage tel que l'API le transporte, miroir de `DecoupageDTO`. */
export interface Decoupage {
  nb_tours: number
}

/**
 * Ce que l'organisateur a choisi à l'écran — la forme **éditable**.
 *
 * Le nombre reste une **chaîne** : un champ vidé doit pouvoir rester vide pendant qu'on le retape,
 * ce qu'un `number` piloté perdrait à chaque frappe (même parti que `EtatSuisse`).
 */
export interface EtatDecoupage {
  tours: string
}

/** Le nombre de tours maximal accepté par l'API (`DecoupageDTO.nb_tours`, `le=64`). */
export const TOURS_MAX_REGLABLES = 64

/** Le réglage de départ : **un** tour, c'est-à-dire la qualification d'un bloc — le défaut actuel. */
export const DECOUPAGE_PAR_DEFAUT: EtatDecoupage = { tours: '1' }

/** Reconstruit l'état d'édition depuis ce que porte l'étape (ou la phase). */
export function depuisDecoupage(decoupage: Decoupage | null): EtatDecoupage {
  if (decoupage === null) return DECOUPAGE_PAR_DEFAUT
  return { tours: String(decoupage.nb_tours) }
}

/**
 * Ce qui part au serveur — ou `undefined` quand la saisie n'est pas exploitable.
 *
 * Même convention que les autres formats : `undefined` veut dire « illisible », **pas** « efface ».
 * L'appelant ne le transmet jamais tel quel, il bloque sa soumission (`estValide`).
 *
 * ⚠️ **Un seul tour rend `null`, pas `{ nb_tours: 1 }`** — et la nuance n'est pas cosmétique. « Non
 * découpée » est l'état par défaut de toute qualification existante ; persister un découpage à 1
 * ferait apparaître un réglage là où l'organisateur n'a rien réglé, et rendrait la relecture d'une
 * base ancienne différente de celle d'une base neuve pour un comportement identique.
 */
export function versDecoupage(etat: EtatDecoupage): Decoupage | null | undefined {
  const nombre = Number(etat.tours)
  if (etat.tours.trim() === '' || !Number.isInteger(nombre)) return undefined
  if (nombre < 1 || nombre > TOURS_MAX_REGLABLES) return undefined
  return nombre === 1 ? null : { nb_tours: nombre }
}

/** Vrai si l'état est soumettable. */
export function estValide(etat: EtatDecoupage): boolean {
  return versDecoupage(etat) !== undefined
}

/**
 * Dit ce que le découpage donne, et **nomme l'écart** quand il ne tombe pas juste.
 *
 * C'est tout l'objet du réglage à l'écran : la règle « des tours égaux » existe côté domaine, mais
 * l'organisateur ne la découvrirait qu'en se faisant refuser son étape. On lui montre la longueur
 * obtenue (« 2 tours de 10 volées »), ou la raison du refus à venir.
 *
 * ⚠️ **`nbVolees` peut être inconnu** (`null`) : l'atelier compose un format de bibliothèque, sans
 * barème posé. On ne promet alors rien plutôt que d'inventer un dénominateur — même parti que la
 * borne du suisse sans effectif.
 */
export function decrireDecoupage(nbVolees: number | null, nbTours: number): string {
  if (nbTours <= 1)
    return 'La qualification se tire d’un seul bloc : aucune pause ne peut s’y poser.'
  if (nbVolees === null || nbVolees < 1) {
    return `${nbTours} tours. La longueur d’un tour dépend du barème du tournoi qui appliquera ce format.`
  }
  if (nbVolees % nbTours !== 0) {
    return `${nbVolees} volées ne se découpent pas en ${nbTours} tours égaux : choisissez un nombre de tours qui divise ${nbVolees}.`
  }
  const parTour = nbVolees / nbTours
  const volees = parTour > 1 ? 'volées' : 'volée'
  return `${nbTours} tours de ${parTour} ${volees}.`
}
