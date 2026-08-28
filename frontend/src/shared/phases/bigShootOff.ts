// Le **modèle** du réglage de Big Shoot Off (E05US028) — logique pure, aucun React.
//
// Séparé du composant comme `poules.ts` : `react-refresh` interdit à un module de rendu d'exporter
// aussi des fonctions, et la conversion « écran ↔ serveur » se teste ici sans DOM. ⚠️ **`paliers`
// est un miroir assumé du domaine** (`ConfigurationBigShootOff.paliers_pour`) : la lecture serveur
// exige un tournoi et une phase posée, alors que l'atelier compose un **format de bibliothèque**.
// Même garde-fou que le serpent des poules — la règle tient en trois lignes, elle est testée, et sa
// dérive ne produirait qu'un aperçu faux, jamais un tournoi faux.

/** Le réglage tel que l'API le transporte, miroir de `ReglageBigShootOffDTO`. */
export interface ReglageBigShootOff {
  eliminations: number[]
  volees: number
  fleches_par_volee: number
  cumul_des_manches: boolean
  departage_les_sortants: boolean
}

/** Ce que l'organisateur a choisi à l'écran — la forme **éditable**, distincte de ce qui part au
 * serveur.
 *
 * Les nombres restent des **chaînes** : un champ vidé doit pouvoir rester vide pendant qu'on le
 * retape. `sortants` est saisi comme **une liste séparée par des virgules** plutôt que par N champs
 * numérotés — le nombre de manches n'est pas connu d'avance (c'est la longueur de la liste), et un
 * organisateur qui pense « 12 → 8 → 4 → 2 » écrit plus vite une suite qu'il n'ajoute quatre lignes.
 */
export interface EtatBigShootOff {
  sortants: string
  volees: string
  fleches: string
  cumul: boolean
  departageSortants: boolean
}

/** Le réglage de départ d'un Big Shoot Off neuf : un sortant par manche, une volée de 3 flèches. */
export const BIG_SHOOT_OFF_PAR_DEFAUT: EtatBigShootOff = {
  sortants: '1',
  volees: '1',
  fleches: '3',
  cumul: false,
  departageSortants: false,
}

/** Reconstruit l'état d'édition depuis ce que porte l'étape (ou la phase). */
export function depuisReglage(reglage: ReglageBigShootOff | null): EtatBigShootOff {
  if (reglage === null) return BIG_SHOOT_OFF_PAR_DEFAUT
  return {
    sortants: reglage.eliminations.join(', '),
    volees: String(reglage.volees),
    fleches: String(reglage.fleches_par_volee),
    cumul: reglage.cumul_des_manches,
    departageSortants: reglage.departage_les_sortants,
  }
}

function entier(valeur: string, minimum: number): number | undefined {
  const nombre = Number(valeur)
  if (valeur.trim() === '' || !Number.isInteger(nombre) || nombre < minimum) return undefined
  return nombre
}

/** Lit la liste de sortants — `undefined` si une seule case est illisible.
 *
 * ⚠️ **Une case à zéro est refusée**, comme côté domaine : « 4, 0, 1 » décrirait une manche qu'on
 * ferait tirer pour rien. On refuse plutôt que de filtrer en silence — filtrer changerait sa liste
 * sans le lui dire. Les séparateurs sont tolérants (virgule, point-virgule, espace) : c'est une
 * aide à la saisie, pas un format à respecter.
 */
export function lireSortants(valeur: string): number[] | undefined {
  const morceaux = valeur
    .split(/[,;\s]+/)
    .map((morceau) => morceau.trim())
    .filter((morceau) => morceau !== '')
  if (morceaux.length === 0) return undefined
  const nombres: number[] = []
  for (const morceau of morceaux) {
    const lu = entier(morceau, 1)
    if (lu === undefined) return undefined
    nombres.push(lu)
  }
  return nombres
}

/**
 * Ce qui part au serveur — ou `undefined` quand la saisie n'est pas encore exploitable.
 *
 * Même convention que `versReglage` des poules : `undefined` veut dire « illisible », **pas**
 * « efface ». L'appelant ne le transmet jamais tel quel, il bloque sa soumission (`estValide`).
 */
export function versReglage(etat: EtatBigShootOff): ReglageBigShootOff | undefined {
  const eliminations = lireSortants(etat.sortants)
  const volees = entier(etat.volees, 1)
  const fleches = entier(etat.fleches, 1)
  if (eliminations === undefined || volees === undefined || fleches === undefined) return undefined
  return {
    eliminations,
    volees,
    fleches_par_volee: fleches,
    cumul_des_manches: etat.cumul,
    departage_les_sortants: etat.departageSortants,
  }
}

/** Vrai si l'état est soumettable. */
export function estValide(etat: EtatBigShootOff): boolean {
  return versReglage(etat) !== undefined
}

/** Ce qu'il **reste** après chaque manche réellement jouable — miroir de `paliers_pour`.
 *
 * On s'arrête à la première manche qui viderait le pas de tir : sortir 2 archers sur 2 ne
 * laisserait personne, donc cette manche ne se joue pas. C'est la règle « on joue tant que la
 * manche est possible », qui rend un format réutilisable sur un effectif qu'il ignore. Rend `[]`
 * sur un effectif illisible : l'écran n'affiche rien plutôt qu'un aperçu inventé.
 */
export function paliers(effectif: number, eliminations: number[]): number[] {
  if (!Number.isInteger(effectif) || effectif < 1) return []
  const suite: number[] = []
  let restant = effectif
  for (const quota of eliminations) {
    if (restant - quota < 1) break
    restant -= quota
    suite.push(restant)
  }
  return suite
}

/**
 * Dit la projection en clair — « 12 → 8 → 6 → 5, cinq rescapés ».
 *
 * ⚠️ **Nomme aussi les manches qui ne se joueront pas.** C'est la contrepartie honnête de « on joue
 * tant que la manche est possible » : le moteur ne refuse rien, mais l'organisateur ne doit pas
 * croire jouer une liste qu'il ne joue pas. Une projection muette sur ce point serait pire qu'un
 * refus, parce qu'elle s'affiche sans avertir.
 */
export function decrireProjection(effectif: number, eliminations: number[]): string {
  const suite = paliers(effectif, eliminations)
  if (suite.length === 0) {
    return `${effectif} inscrits : aucune manche jouable avec cette liste.`
  }
  const chemin = [effectif, ...suite].join(' → ')
  const restants = suite[suite.length - 1] ?? effectif
  const pluriel = restants > 1 ? 'rescapés' : 'rescapé'
  const ignorees = eliminations.length - suite.length
  const reste =
    ignorees > 0
      ? ` — les ${ignorees === 1 ? 'dernière manche ne se jouera pas' : `${ignorees} dernières manches ne se joueront pas`}`
      : ''
  return `${chemin} : ${restants} ${pluriel}${reste}.`
}
