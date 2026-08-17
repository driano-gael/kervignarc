// Présentation publique du **Big Shoot Off** (E05US031) — logique pure, testée en node.
//
// Extraite du composant plutôt qu'écrite dans le JSX : c'est l'enseignement d'ADR-0064 §2 (*une
// garantie annoncée n'existe que si un chemin de code la produit — et qu'un test l'exerce*). L'ordre
// des finalistes est une **règle de lecture**, pas une mise en forme : il doit pouvoir échouer dans
// un test plutôt que sur un écran projeté.

import type { EtatBigShootOffPublic, TireurPublic } from './api'

/** Un finaliste, prêt à afficher : son nom rédigé, son sort, et ses scores par manche. */
export interface LigneTireur {
  archer_id: number
  nom: string
  /** `null` tant qu'il est **en lice** — un rang annoncé avant la sortie serait un faux départ. */
  rang: number | null
  scores: number[]
}

export function estSorti(ligne: LigneTireur): boolean {
  return ligne.rang !== null
}

/** Combien d'archers **tirent encore**, maintenant.
 *
 * ⚠️ Ce n'est **pas** `projection.restants`, et la confusion a coûté un défaut relevé en revue :
 * `restants` vaut `paliers[-1]`, c'est-à-dire l'effectif **à la fin** du format — une constante de
 * la phase, connue avant le premier tir. L'afficher comme « en lice » annonçait « 1 archer en
 * lice » du début à la fin d'une finale à un rescapé. Le seul état qui dise qui tire encore est la
 * population elle-même. */
export function nbEnLice(etat: EtatBigShootOffPublic): number {
  return etat.tireurs.filter((tireur) => tireur.rang === null).length
}

/** Le mot de la colonne « Sort » — jamais une couleur seule (`DV-03`).
 *
 * ⚠️ `rang` reste `null` pour le **rescapé** : le serveur ne range que les éliminés
 * (`ServiceBigShootOff` n'attribue un rang qu'à la sortie). Sans le cas `termine`, le vainqueur de
 * la finale restait donc affiché « En lice » jusqu'au soir, alors que le palmarès le donne 1ᵉʳ.
 * Au pluriel (`restants > 1`, une échelle qui s'arrête à plusieurs), aucun des rescapés n'est
 * vainqueur de personne : on dit « Qualifié ». */
export function libelleSort(ligne: LigneTireur, etat: EtatBigShootOffPublic): string {
  if (ligne.rang !== null) return `${ligne.rang}ᵉ`
  if (!etat.termine) return 'En lice'
  return nbEnLice(etat) === 1 ? 'Vainqueur' : 'Qualifié'
}

/** Les finalistes dans l'ordre de lecture : **ceux qui tirent encore d'abord**, puis les sortis du
 * mieux classé au dernier.
 *
 * ⚠️ **L'ordre du serveur n'est pas celui-là**, et s'en contenter serait un contresens de lecture :
 * `tireurs` suit l'ordre de composition de la phase, si bien qu'un archer éliminé à la première
 * manche pouvait ouvrir le tableau pendant que les quatre finalistes restants se disputaient le
 * titre dessous. Un écran de salle se lit de haut en bas, et ce qui se joue doit être en haut.
 *
 * ⚠️ **`rang` croissant chez les sortis, donc le meilleur en tête.** Le Big Shoot Off élimine par le
 * bas : le dernier sorti porte le plus petit rang. Trier par ordre de sortie mettrait le 12ᵉ en
 * premier — l'inverse de ce qu'on vient chercher.
 */
export function lignesTireurs(etat: EtatBigShootOffPublic): LigneTireur[] {
  return [...etat.tireurs]
    .sort((a, b) => {
      if (a.rang === null && b.rang === null) {
        // ⚠️ **Par NOM puis prénom, et le tri se fait AVANT de composer la ligne** (correctif : le
        // premier jet triait la chaîne rédigée « Prénom NOM », donc **par prénom** — une liste
        // d'archers ne se lit pas comme ça, et le défaut ne se voyait que sur deux noms bien
        // choisis). `localeCompare` en `'fr'` pour que les accents tombent à leur place.
        return a.nom.localeCompare(b.nom, 'fr') || a.prenom.localeCompare(b.prenom, 'fr')
      }
      if (a.rang === null) return -1
      if (b.rang === null) return 1
      return a.rang - b.rang
    })
    .map(versLigne)
}

function versLigne(tireur: TireurPublic): LigneTireur {
  return {
    archer_id: tireur.archer_id,
    // Le nom vient de la phase, jamais d'un cache client : un archer renommé garde son suivi sans
    // afficher un nom périmé.
    nom: `${tireur.prenom} ${tireur.nom}`.trim(),
    // `en_lice` et `rang` disent la même chose côté serveur (`rang` est `null` tant qu'on est en
    // lice) ; on retient **`rang`**, la seule des deux qui porte aussi la place obtenue. Les croiser
    // à l'affichage rendrait un état incohérent indétectable.
    rang: tireur.rang,
    scores: [...tireur.scores],
  }
}
