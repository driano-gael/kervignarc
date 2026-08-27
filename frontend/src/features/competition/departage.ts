// Ex æquo et règle de départage — retour maquettes du 04/08/2026 (A16) : *« la règle de départage
// doit-elle être affichée en permanence, ou seulement en cas d'ex æquo ? → seulement en cas d'ex
// aequo. »*
//
// Les colonnes « 10 » et « 9 » ne sont pas la règle, ce sont des **données** : elles restent. Ce
// qui disparaît, c'est la **phrase de règle** affichée en permanence — un écran qui explique en
// continu une règle qui ne s'applique pas finit par ne plus être lu. Corollaire : il faut alors
// **montrer sur qui**, d'où `totauxExAequo`, sans quoi on annoncerait une devinette.

/** Ce qu'il faut d'une ligne de classement pour raisonner sur les égalités. Structurel plutôt que
 * `LigneClassement` : la fonction est testable avec trois champs, et le palmarès pourra la
 * réemployer sans partager le type de la qualification. */
export interface LigneDepartageable {
  total: number
  statut: string
  categorie_id: number
}

/** Les totaux **à égalité** au sein d'une même catégorie, par catégorie.
 *
 * Par catégorie et non sur tout le tableau : le départage FFTA ordonne un **classement**, et celui
 * qui compte pour un archer est celui de sa catégorie — deux archers de catégories différentes au
 * même total ne se disputent rien. Les archers **hors course** sont écartés : leur score reste
 * affiché, mais signaler leur égalité annoncerait un départage qui n'aura jamais lieu (ADR-0050).
 */
export function totauxExAequo(lignes: readonly LigneDepartageable[]): Map<number, Set<number>> {
  const vus = new Map<number, Map<number, number>>()
  for (const ligne of lignes) {
    if (ligne.statut !== 'en_lice') continue
    // ⚠️ **Un total nul n'est pas un score, c'est une absence de score.** Le domaine crée une ligne
    // `EN_LICE` pour *chaque* inscrit, qu'il ait tiré ou non (`calculer_classement`) : avant la
    // première volée, les 120 archers sont à zéro. Les compter ferait de tout le monde un ex æquo et
    // afficherait la règle de départage **en permanence** toute la matinée — c'est-à-dire très
    // exactement ce qu'A16 demandait de supprimer. Le défaut a été trouvé en revue (axes C1 et
    // adversarial) ; il rendait la fonctionnalité contraire à son propre CA.
    // DETTE-041 — approximation de `a_tire`, que le DTO n'expose pas. Cf. registre.
    if (ligne.total === 0) continue
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

/** Y a-t-il au moins une égalité à départager **dans cette liste** ?
 *
 * ⚠️ **Ce n'est plus la condition d'affichage de la règle** (E16US004) : depuis que le classement
 * peut être centré, les égalités se **calculent** sur la liste complète mais ne s'**annoncent**
 * que si une ligne visible les porte. Conservée parce qu'elle exprime l'invariant du module («
 * aucune égalité fantôme ») et que les tests s'en servent. Plus aucun appelant en production.
 */
export function aDesExAequo(egalites: ReadonlyMap<number, ReadonlySet<number>>): boolean {
  return egalites.size > 0
}
