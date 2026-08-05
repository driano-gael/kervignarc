// Ex æquo et règle de départage — retour maquettes du 04/08/2026 (A16).
//
// *« La règle de départage doit-elle être affichée en permanence, ou seulement en cas d'ex æquo ?
// → seulement en cas d'ex aequo. »*
//
// **Ce que cela change, et ce que cela ne change pas.** Les colonnes « 10 » et « 9 » ne sont pas la
// règle, ce sont des **données** — le nombre de 10 et de 9 de chaque archer, qui se lit pour
// lui-même. Elles restent. Ce qui disparaît, c'est la **phrase de règle** (« à total égal, plus de
// 10, puis plus de 9 ») affichée en permanence : elle n'apprend rien tant que personne n'est à
// égalité, et un écran qui explique en continu une règle qui ne s'applique pas finit par ne plus
// être lu du tout.
//
// Corollaire utile : si l'on n'affiche la règle qu'au moment où elle s'applique, encore faut-il
// **montrer sur qui**. D'où `totauxExAequo`, qui sert à marquer les lignes concernées — sans quoi on
// afficherait « il y a des ex æquo » sans dire lesquels, ce qui est une devinette.

/** Ce qu'il faut d'une ligne de classement pour raisonner sur les égalités. Structurel plutôt que
 * `LigneClassement` : la fonction est testable avec trois champs, et le palmarès pourra la
 * réemployer sans partager le type de la qualification. */
export interface LigneDepartageable {
  total: number
  statut: string
  categorie_id: number
}

/**
 * Les totaux **à égalité** au sein d'une même catégorie, par catégorie.
 *
 * Pourquoi par catégorie et non sur tout le tableau : le départage FFTA sert à ordonner un
 * **classement**, et le classement qui compte pour un archer est celui de sa catégorie. Deux archers
 * de catégories différentes au même total ne sont pas ex æquo, ils ne se disputent rien.
 *
 * Les archers **hors course** (abandon, disqualification) sont écartés : leur score reste affiché,
 * mais ils ne sont plus classés — les faire entrer dans une égalité signalerait un départage qui
 * n'aura jamais lieu (cf. ADR-0050).
 */
export function totauxExAequo(lignes: readonly LigneDepartageable[]): Map<number, Set<number>> {
  const vus = new Map<number, Map<number, number>>()
  for (const ligne of lignes) {
    if (ligne.statut !== 'en_lice') continue
    const parTotal = vus.get(ligne.categorie_id) ?? new Map<number, number>()
    parTotal.set(ligne.total, (parTotal.get(ligne.total) ?? 0) + 1)
    vus.set(ligne.categorie_id, parTotal)
  }

  const resultat = new Map<number, Set<number>>()
  for (const [categorie, parTotal] of vus) {
    const egaux = new Set<number>()
    for (const [total, nombre] of parTotal) if (nombre > 1) egaux.add(total)
    if (egaux.size > 0) resultat.set(categorie, egaux)
  }
  return resultat
}

/** Cette ligne est-elle à égalité avec une autre de sa catégorie ? */
export function estExAequo(
  ligne: LigneDepartageable,
  egalites: ReadonlyMap<number, ReadonlySet<number>>,
): boolean {
  if (ligne.statut !== 'en_lice') return false
  return egalites.get(ligne.categorie_id)?.has(ligne.total) === true
}

/** Y a-t-il au moins une égalité à départager ? C'est la condition d'affichage de la règle. */
export function aDesExAequo(egalites: ReadonlyMap<number, ReadonlySet<number>>): boolean {
  return egalites.size > 0
}
