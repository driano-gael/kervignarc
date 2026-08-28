// Les frappes en cours, non encore enregistrées — logique **pure**, testée sans rendu.
//
// Le tampon de frappe vivait dans `PaveArcher`, monté avec une clé par archer : tout ce qui
// démontait ce composant jetait la volée en cours sans un mot, et quatre chemins le démontent —
// changer d'archer, ouvrir « Où tire-t-on ensuite ? », changer de départ, fermer le pavé.
// L'extraire ici rend la garantie **vérifiable**. Ce n'est pas de l'état serveur — donc ni React
// Query ni store persisté : une frappe à moitié tapée n'a pas à survivre à l'onglet, et la faire
// survivre poserait la question de sa péremption.

/** Les brouillons de tous les archers de la cible, indexés par `archerId:numeroDeVolee`. */
export type Brouillons = Record<string, string[]>

/** La clé d'un brouillon. Un archer peut avoir une frappe en cours sur **chaque** volée : revenir
 * corriger la volée 3 ne doit pas écraser ce qu'on avait commencé sur la 4. */
export function cleBrouillon(archerId: number, numero: number): string {
  return `${archerId}:${numero}`
}

/** Le brouillon d'une volée, ou `undefined` s'il n'y en a pas — auquel cas l'appelant retombe sur le
 * contenu **persisté** de la volée. */
export function lireBrouillon(
  brouillons: Brouillons,
  archerId: number,
  numero: number,
): string[] | undefined {
  return brouillons[cleBrouillon(archerId, numero)]
}

/**
 * Note (ou efface, avec `null`) le brouillon d'une volée. Rend un **nouvel objet** — jamais de
 * mutation : c'est de l'état React, le muter en place ne redéclencherait aucun rendu.
 *
 * Effacer un brouillon absent rend l'objet **inchangé** (même référence) : sans cette garde, chaque
 * enregistrement de volée produirait un objet neuf et ferait re-rendre toute la grille pour rien.
 */
export function noterBrouillon(
  brouillons: Brouillons,
  archerId: number,
  numero: number,
  valeurs: string[] | null,
): Brouillons {
  const cle = cleBrouillon(archerId, numero)
  if (valeurs === null) {
    if (!(cle in brouillons)) return brouillons
    const suite = { ...brouillons }
    delete suite[cle]
    return suite
  }
  return { ...brouillons, [cle]: valeurs }
}
