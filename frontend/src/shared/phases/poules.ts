// Le **modèle** du réglage de poules (E05US023, ADR-0083) — logique pure, aucun React.
//
// Séparé du composant pour la même raison que `profondeur.ts` : la règle `react-refresh` interdit à
// un module de rendu d'exporter aussi des fonctions, et surtout la conversion « ce que l'écran
// affiche ↔ ce qui part au serveur » se teste ici sans monter le moindre DOM.
//
// ⚠️ **`repartition` est un miroir assumé du domaine** (`domain/poule.py : nb_poules_pour` et
// `composer_poules`). Le calcul vit **aussi** côté serveur, où il fait autorité
// (`GET /api/v1/poules/repartition/...`) — mais cette lecture-là exige un tournoi et une phase
// posée, alors que l'atelier compose un **format de bibliothèque**, sans tournoi. Il n'y a donc pas
// d'appel possible, et un aller-retour par frappe serait de toute façon le mauvais outil pour une
// aide à la saisie. Le miroir a un précédent (`EFFECTIF_MAX`, `RANGS_DU_PODIUM`) et un garde-fou :
// il tient en deux règles, toutes deux testées ci-contre, et sa dérive ne produirait qu'un aperçu
// faux — jamais un tournoi faux, puisque c'est le serveur qui compose le jour J.

/** Ce que rapporte une rencontre — victoire / nul / défaut, défaut FFTA du club : 3 / 1 / 0. */
export interface BaremePoule {
  victoire: number
  nul: number
  defaite: number
}

/**
 * Comment les groupes sont composés (E05US029) — miroir de `domain.poule.ModeDeComposition`.
 *
 * `serpent` équilibre la force des groupes (1→A, 2→B, 3→C, 4→C…), ce qui est juste quand personne
 * ne connaît encore les niveaux. `par_niveau` fait l'inverse et c'est voulu : un groupe par tranche
 * de rangs contiguë, la poule A réunissant les meilleurs — le format club en cascade.
 */
export type ModeDeComposition = 'serpent' | 'par_niveau'

/** Le réglage tel que l'API le transporte, miroir de `ReglagePoulesDTO`. */
export interface ReglagePoules {
  taille_visee: number
  bareme: BaremePoule | null
  nb_qualifies: number | null
  rencontres_par_archer: number | null
  departage_inter_poules: boolean
  mode: ModeDeComposition
  serpent_assume: boolean
}

/**
 * Ce que l'organisateur a choisi à l'écran — la forme **éditable**, distincte de ce qui part au
 * serveur.
 *
 * Les nombres restent des **chaînes** : un champ vidé doit pouvoir rester vide pendant qu'on le
 * retape, ce qu'un `number` piloté ferait perdre à chaque frappe (même parti que `EtatProfondeur`
 * et que le barème de qualification).
 *
 * `produit` porte le **régime d'ex æquo** (ADR-0083 §5) : « classement » (la poule classe, tout
 * ex æquo irréductible se départage au barrage) ou « qualifiés » (seule la barre compte). Ce n'est
 * pas un champ de plus en base — c'est la présence ou l'absence de `nb_qualifies` —, mais l'écran
 * doit le poser en question plutôt que de le laisser déduire d'un champ laissé vide.
 */
export interface EtatPoules {
  taille: string
  produit: 'classement' | 'qualifies'
  qualifies: string
  victoire: string
  nul: string
  defaite: string
  departage: boolean
  mode: ModeDeComposition
  serpentAssume: boolean
}

/** Le réglage de départ d'une phase de poules neuve : des poules de 4, barème 3 / 1 / 0. */
export const POULES_PAR_DEFAUT: EtatPoules = {
  taille: '4',
  produit: 'classement',
  qualifies: '2',
  victoire: '3',
  nul: '1',
  defaite: '0',
  departage: false,
  mode: 'serpent',
  serpentAssume: false,
}

/** Reconstruit l'état d'édition depuis ce que porte l'étape (ou la phase). */
export function depuisReglage(reglage: ReglagePoules | null): EtatPoules {
  if (reglage === null) return POULES_PAR_DEFAUT
  const bareme = reglage.bareme
  return {
    taille: String(reglage.taille_visee),
    produit: reglage.nb_qualifies === null ? 'classement' : 'qualifies',
    qualifies: String(reglage.nb_qualifies ?? POULES_PAR_DEFAUT.qualifies),
    victoire: String(bareme?.victoire ?? POULES_PAR_DEFAUT.victoire),
    nul: String(bareme?.nul ?? POULES_PAR_DEFAUT.nul),
    defaite: String(bareme?.defaite ?? POULES_PAR_DEFAUT.defaite),
    departage: reglage.departage_inter_poules,
    // ⚠️ `?? 'serpent'` plutôt qu'un accès direct : une étape enregistrée avant E05US029 n'a pas
    // la clé (le backend ne l'écrit qu'au mode non-défaut, pour éviter une migration), et le
    // serpent est très exactement ce qu'elle jouait.
    mode: reglage.mode ?? 'serpent',
    serpentAssume: reglage.serpent_assume ?? false,
  }
}

function entier(valeur: string, minimum: number): number | undefined {
  const nombre = Number(valeur)
  if (valeur.trim() === '' || !Number.isInteger(nombre) || nombre < minimum) return undefined
  return nombre
}

/**
 * Ce qui part au serveur — ou `undefined` quand la saisie n'est pas encore exploitable.
 *
 * Même convention que `versProfondeur` : `undefined` veut dire « illisible », **pas** « efface ».
 * L'appelant ne le transmet jamais tel quel, il bloque sa soumission (`estValide`).
 *
 * Les invariants **du domaine** ne sont pas recopiés ici — un barème qui récompense la défaite, plus
 * de qualifiés que de membres : `ReglageDePoules` les refuse en 422, et les redoubler à l'écran
 * donnerait deux messages pour une faute. On ne borne que ce qui empêche de **construire** l'objet.
 */
export function versReglage(etat: EtatPoules): ReglagePoules | undefined {
  const taille = entier(etat.taille, 2)
  const victoire = entier(etat.victoire, 0)
  const nul = entier(etat.nul, 0)
  const defaite = entier(etat.defaite, 0)
  if (taille === undefined || victoire === undefined || nul === undefined || defaite === undefined)
    return undefined
  let qualifies: number | null = null
  if (etat.produit === 'qualifies') {
    const lu = entier(etat.qualifies, 1)
    if (lu === undefined) return undefined
    qualifies = lu
  }
  return {
    taille_visee: taille,
    bareme: { victoire, nul, defaite },
    nb_qualifies: qualifies,
    rencontres_par_archer: null,
    departage_inter_poules: etat.departage,
    mode: etat.mode,
    // La dérogation n'a de sens **que** sous le serpent : l'envoyer depuis un réglage par niveau
    // laisserait une case armée qui ressusciterait au retour au serpent, sans que personne ne
    // l'ait cochée pour ce réglage-là.
    serpent_assume: etat.mode === 'serpent' && etat.serpentAssume,
  }
}

/** Vrai si l'état est soumettable. */
export function estValide(etat: EtatPoules): boolean {
  return versReglage(etat) !== undefined
}

/**
 * La répartition qu'un effectif produirait — **la même règle que le serveur**, en deux temps.
 *
 * 1. Le nombre de groupes est `effectif ÷ taille` **arrondi vers le bas**, au moins 1
 *    (`nb_poules_pour`). C'est l'arbitrage du 09/08/2026 : aucune poule ne compte **moins** que la
 *    taille demandée, quitte à en gonfler quelques-unes. 30 archers en poules de 4 → 7 poules.
 * 2. Le reste **gonfle** quelques groupes d'une unité, et l'on rejoue le **serpent lui-même** pour
 *    savoir lesquels : 30 en 7 poules → deux de 5 (les poules 1 et 2) puis cinq de 4.
 *
 * ⚠️ **Ce ne sont pas toujours les groupes de tête**, et le supposer était faux. Le serpent
 * distribue par passages alternés (`divmod(index, nb)` puis inversion un passage sur deux) : quand
 * le dernier passage est **impair**, il repart de la fin, et ce sont les groupes de **queue** qui
 * reçoivent l'archer supplémentaire — 10 archers en poules de 3 gonflent la poule 3, pas la poule 1.
 * On recopie donc la boucle du domaine plutôt que son résultat supposé.
 *
 * Rend `[]` sur un effectif ou une taille illisible : l'écran n'affiche alors rien plutôt qu'un
 * aperçu inventé.
 */
export function repartition(
  effectif: number,
  taille: number,
  mode: ModeDeComposition = 'serpent',
): number[] {
  if (!Number.isInteger(effectif) || effectif < 1) return []
  if (!Number.isInteger(taille) || taille < 2) return []
  const groupes = Math.max(1, Math.floor(effectif / taille))
  if (mode === 'par_niveau') {
    // Les `surplus` **derniers** groupes gonflent d'une unité — le bas absorbe le reste (arbitrage
    // du cadrage du 21/08/2026). On recopie la règle du domaine (`_tranches_de_niveau`), pas son
    // résultat supposé, exactement comme la boucle du serpent ci-dessous.
    const base = Math.floor(effectif / groupes)
    const surplus = effectif % groupes
    return Array.from({ length: groupes }, (_, numero) =>
      numero >= groupes - surplus ? base + 1 : base,
    )
  }
  const tailles = Array.from({ length: groupes }, () => 0)
  for (let index = 0; index < effectif; index += 1) {
    const passage = Math.floor(index / groupes)
    const position = index % groupes
    const groupe = passage % 2 === 0 ? position : groupes - 1 - position
    tailles[groupe] = (tailles[groupe] ?? 0) + 1
  }
  return tailles
}

/**
 * Les **tranches de rangs** que des poules de niveau disputent — « 1-6, 7-12, 13-18 ».
 *
 * Dérivées du cumul des `tailles`, jamais transportées par l'API : ce sont deux façons de dire la
 * même chose, et en envoyer une seconde depuis le serveur créerait la divergence que le miroir de
 * ce module prend soin d'éviter (une répartition affichée qui ne serait pas celle jouée).
 */
export function tranchesDeRangs(tailles: number[]): Array<[number, number]> {
  const tranches: Array<[number, number]> = []
  let debut = 1
  for (const taille of tailles) {
    tranches.push([debut, debut + taille - 1])
    debut += taille
  }
  return tranches
}

/**
 * Dit une répartition en clair — « 7 poules : deux de 5, cinq de 4 ».
 *
 * Par niveau, ce ne sont pas les *tailles* qui renseignent l'organisateur mais les **rangs** que
 * chaque groupe dispute : « 6 poules de niveau : rangs 1-6, 7-12, … » (le CA le formule ainsi
 * verbatim). Les tailles y restent lisibles — la tranche les donne par ses bornes.
 */
export function decrireRepartition(tailles: number[], mode: ModeDeComposition = 'serpent'): string {
  if (tailles.length === 0) return ''
  if (mode === 'par_niveau') {
    const rangs = tranchesDeRangs(tailles)
      .map(([debut, fin]) => `${debut}-${fin}`)
      .join(', ')
    const pluriel = tailles.length > 1 ? 'poules de niveau' : 'poule de niveau'
    return `${tailles.length} ${pluriel} : rangs ${rangs}`
  }
  const parTaille = new Map<number, number>()
  for (const taille of tailles) parTaille.set(taille, (parTaille.get(taille) ?? 0) + 1)
  const groupes = [...parTaille.entries()]
    .sort((a, b) => b[0] - a[0])
    .map(([taille, combien]) => `${combien} de ${taille}`)
    .join(', ')
  const pluriel = tailles.length > 1 ? 'poules' : 'poule'
  return `${tailles.length} ${pluriel} : ${groupes}`
}

/**
 * Le mot à employer pour les groupes d'une phase — « poules » ou « poules de niveau ».
 *
 * Extrait plutôt que rendu en ternaire dans le JSX (E05US029) : c'est du **vocabulaire**, il doit
 * être dit d'une seule façon partout et se tester sans monter de DOM. Le mode est optionnel parce
 * qu'une réponse d'API d'avant cette US ne le porte pas — et « poules » est alors exact.
 */
export function motDeGroupe(mode: ModeDeComposition | undefined): string {
  return mode === 'par_niveau' ? 'poules de niveau' : 'poules'
}
