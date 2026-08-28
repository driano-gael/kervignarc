// Ce qu'une rencontre **rédigée** dit à qui la lit sans la saisir — logique pure (E05US031).
//
// Trois formats servent au public la même forme de rencontre (poules, suisse, arbre de duels) ;
// écrire la ligne trois fois l'aurait fait diverger sur la seule chose qui compte. ⚠️ **Ce n'est
// pas un « remède structurel »** : les deux occurrences supplémentaires n'existaient pas avant ce
// diff. ⚠️ **`DuellisteLisible` est redéclaré ici plutôt qu'importé** d'une feature — un module de
// `shared/` qui importe d'une feature est l'inversion que `shared/salle/place.ts` documente comme
// la seule du front, et qu'elle a corrigée. Le typage structurel fait le reste.

/** Un duelliste, réduit à ce qu'une ligne de rencontre a besoin de nommer. */
export interface DuellisteLisible {
  archer_id: number
  nom: string
  prenom: string
}

/** La forme minimale d'une rencontre **rédigée**, commune aux trois formats.
 *
 * Volontairement pauvre : ni pavé, ni manches, ni validateur. La typer sur l'un des trois DTO
 * interdirait de la réutiliser sur les deux autres. `termine` et `validee` disent deux choses
 * distinctes — le tir est allé au bout / le scoreur a scellé —, et c'est **entre les deux** que le
 * public lit « en attente de validation ».
 */
export interface RencontreLisible {
  haut: DuellisteLisible | null
  bas: DuellisteLisible | null
  points_haut: number | null
  points_bas: number | null
  vainqueur: string | null
  termine: boolean
  validee: boolean
  desynchronisee: boolean
}

/** Le nom affiché d'un duelliste. `trim` couvre un prénom vide, que l'import tolère. */
export function nomComplet(qui: DuellisteLisible): string {
  return `${qui.prenom} ${qui.nom}`.trim()
}

/** L'état d'une rencontre en un mot, **pour le public**.
 *
 * ⚠️ Distinct d'`etatRencontre` (`features/suisse/presentation.ts`), qui lit le `duel` de saisie :
 * le DTO public ne porte rien de tout cela (règle 6). ⚠️ **Les deux vocabulaires se recouvrent sans
 * être identiques** — l'écran public ne connaît qu'« en attente de validation » là où la tablette
 * distingue deux états de saisie : réduction voulue, pas divergence. `desynchronisee` **prime** :
 * une rencontre bloquée n'est pas « à tirer », l'annoncer ferait attendre des archers pour rien.
 */
export function etatRencontre(rencontre: RencontreLisible): string {
  if (rencontre.desynchronisee) return 'tir mis de côté'
  if (rencontre.validee) return 'validée'
  if (rencontre.termine) return 'en attente de validation'
  return 'à tirer'
}

/** Le score d'une rencontre, ou `null` si rien n'est encore départagé.
 *
 * Rendu **dès que les deux points existent**, sans attendre la validation : c'est ce que la salle
 * voit sur les cibles, et le taire jusqu'au sceau ferait mentir l'écran pendant le temps — parfois
 * long — où le scoreur descend la ligne. L'état de la rencontre, lui, dit que ce n'est pas scellé.
 */
export function scoreRencontre(rencontre: RencontreLisible): string | null {
  if (rencontre.points_haut === null || rencontre.points_bas === null) return null
  return `${rencontre.points_haut} — ${rencontre.points_bas}`
}

/** Le côté vainqueur, mais **seulement** une fois la rencontre validée.
 *
 * Le serveur remplit `vainqueur` dès que le tir est terminé ; le mettre en gras avant le sceau
 * annoncerait un résultat qu'une correction peut encore renverser. Même parti que `LigneDuel`
 * (`features/tableaux`), d'où cette fonction est tirée.
 */
export function gagnantAffiche(rencontre: RencontreLisible): 'haut' | 'bas' | null {
  if (!rencontre.validee) return null
  return rencontre.vainqueur === 'haut' ? 'haut' : rencontre.vainqueur === 'bas' ? 'bas' : null
}

/** Les archers d'une rencontre, pour savoir si un archer suivi y figure. */
export function participants(rencontre: RencontreLisible): number[] {
  return [rencontre.haut, rencontre.bas]
    .filter((qui): qui is DuellisteLisible => qui !== null)
    .map((qui) => qui.archer_id)
}
