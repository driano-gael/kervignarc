// Logique pure de la saisie d'un barrage (E06US003, ADR-0066) — extraite du composant pour être
// testable seule, comme `format.ts` et `routage/presentation.ts`.
//
// Deux règles y vivent, et toutes deux protègent contre une **saisie incomplète qui ferait perdre
// quelqu'un** :
//
// - un groupe se retire **en entier** — le serveur refuse une manche à moitié tirée, et on le dit
//   avant d'émettre la requête plutôt que de laisser partir un 422 ;
// - « pas encore noté » n'est **pas** « absent ». L'absence est une issue réglementaire
//   (B.6.5.2.4 : l'archer est déclaré perdant) ; elle se **coche**, elle ne se déduit jamais d'un
//   champ vide. Confondre les deux ferait éliminer un archer que le scoreur n'a pas encore saisi.

import type { TirBarrage } from './api'

export interface SaisieTir {
  score: string
  distance: string
  absent: boolean
}

export const TIR_VIERGE: SaisieTir = { score: '', distance: '', absent: false }

/** Ce groupe peut-il être soumis ? Chaque tireur doit être **noté ou déclaré absent**. */
export function mancheComplete(groupe: number[], saisies: Record<number, SaisieTir>): boolean {
  return groupe.every((archerId) => {
    const tir = saisies[archerId] ?? TIR_VIERGE
    return tir.absent || tir.score.trim() !== ''
  })
}

/** Traduit la saisie d'écran en tirs pour l'API.
 *
 * ⚠️ `score: null` signifie **absent**, et `distance_au_centre: null` **mesure non faite** — qui
 * n'est pas une distance nulle : le moteur refuse de départager sur une inconnue et fait retirer.
 * Un champ distance laissé vide est donc le cas **normal** (le juge mesure la flèche litigieuse,
 * rarement les deux), pas une saisie bâclée.
 */
export function versTirs(groupe: number[], saisies: Record<number, SaisieTir>): TirBarrage[] {
  return groupe.map((archerId) => {
    const tir = saisies[archerId] ?? TIR_VIERGE
    return {
      archer_id: archerId,
      score: tir.absent ? null : Number(tir.score),
      distance_au_centre: tir.distance.trim() === '' ? null : Number(tir.distance),
    }
  })
}

/** Pré-remplit le formulaire depuis des tirs **déjà enregistrés** — correction d'une manche.
 *
 * ⚠️ `score === null` **recoche « absent »**, il ne laisse pas un champ vide. Dans ce domaine, un
 * score nul *est* l'absence réglementaire ; « pas encore noté » n'a pas de ligne du tout. Rouvrir
 * la correction avec un champ vide changerait donc le sens de ce qui avait été saisi — et le
 * bouton resterait grisé, `mancheComplete` exigeant une note ou une case cochée.
 */
export function depuisTirs(tirs: TirBarrage[] | undefined): Record<number, SaisieTir> {
  const saisies: Record<number, SaisieTir> = {}
  for (const tir of tirs ?? []) {
    saisies[tir.archer_id] = {
      score: tir.score === null ? '' : String(tir.score),
      distance: tir.distance_au_centre === null ? '' : String(tir.distance_au_centre),
      absent: tir.score === null,
    }
  }
  return saisies
}

/** Un archer répond-il à la recherche ? Casse **et accents** repliés.
 *
 * ⚠️ Sans le repli des diacritiques, « Créac'h » ne répondait pas à « creach » — ce qui compte
 * dans un club breton, et c'est le genre de détail qui rend une liste de 120 noms inutilisable au
 * doigt. Même parti que `domain.club.cle_nom` côté serveur.
 */
export function correspond(nom: string, prenom: string, recherche: string): boolean {
  const replier = (texte: string) =>
    texte
      .normalize('NFD')
      .replace(/\p{Diacritic}/gu, '')
      .toLowerCase()
  const terme = replier(recherche.trim())
  return terme === '' || replier(`${nom} ${prenom}`).includes(terme)
}
