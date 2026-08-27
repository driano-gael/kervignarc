// Le **modèle** du réglage de poules (E05US023, ADR-0083) — logique pure, aucun React.
//
// Séparé du composant comme `profondeur.ts` : `react-refresh` interdit à un module de rendu
// d'exporter aussi des fonctions, et la conversion « écran ↔ serveur » se teste sans DOM. ⚠️
// **`repartition` est un miroir assumé du domaine** (`domain/poule.py`) : la lecture serveur exige
// un tournoi et une phase posée, alors que l'atelier compose un **format de bibliothèque**. La
// dérive ne produirait qu'un aperçu faux — jamais un tournoi faux, le serveur composant le jour J.

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
  /**
   * ⚠️ **Optionnels, et c'est le type qui doit le dire** (correctif de revue).
   *
   * Les déclarer requis obligeait `depuisReglage` à se défendre d'une absence que le type disait
   * impossible, et le test de ce repli devait fabriquer un objet illégal par `as unknown as` — un
   * double cast ne prouve rien, il empêche seulement `tsc` de dire que le cas est impossible.
   */
  mode?: ModeDeComposition
  serpent_assume?: boolean
}

/** Ce que l'organisateur a choisi à l'écran — la forme **éditable**, distincte de ce qui part au
 * serveur.
 *
 * Les nombres restent des **chaînes** : un champ vidé doit pouvoir rester vide pendant qu'on le
 * retape, ce qu'un `number` piloté ferait perdre à chaque frappe. `produit` porte le **régime d'ex
 * æquo** (ADR-0083 §5) — ce n'est pas un champ de plus en base (c'est la présence de
 * `nb_qualifies`), mais l'écran doit le poser en question plutôt que le laisser déduire d'un vide.
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

/** Ce qui part au serveur — ou `undefined` quand la saisie n'est pas encore exploitable.
 *
 * Même convention que `versProfondeur` : `undefined` veut dire « illisible », **pas** « efface » ;
 * l'appelant bloque sa soumission (`estValide`). ⚠️ Les invariants **du domaine** ne sont pas
 * recopiés ici — `ReglageDePoules` les refuse en 422, et les redoubler donnerait deux messages pour
 * une faute. On ne borne que ce qui empêche de **construire** l'objet.
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
    // ⚠️ Miroir exact de `serpent_assume` ci-dessous, et pour la même raison (correctif de
    // 2ᵉ passe, relevé par quatre axes) : le domaine **refuse** `nb_qualifies` sous « par niveau »
    // — les qualifiés y formeraient un peigne de rangs qu'aucun prélèvement ne sait désigner.
    // L'émettre quand même faisait répondre 422 à un formulaire que l'écran déclarait valide.
    nb_qualifies: etat.mode === 'par_niveau' ? null : qualifies,
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

/** La répartition qu'un effectif produirait — **la même règle que le serveur**, en deux temps.
 *
 * Le nombre de groupes est `effectif ÷ taille` **arrondi vers le bas**, au moins 1 (arbitrage du
 * 09/08/2026 : aucune poule ne compte moins que la taille demandée) ; le reste **gonfle** quelques
 * groupes, et l'on rejoue le **serpent** pour savoir lesquels. ⚠️ **Ce ne sont pas toujours les
 * groupes de tête** : quand le dernier passage est impair, le serpent repart de la fin. `[]` sur
 * une saisie illisible. ⚠️ `// DETTE-076` — miroir inscrit au registre, sans test de contrat.
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
