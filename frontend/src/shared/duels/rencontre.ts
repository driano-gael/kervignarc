// Ce qu'une rencontre **rédigée** dit à qui la lit sans la saisir — logique pure, aucun React
// (E05US031).
//
// Trois formats servent au public la même forme de rencontre : les poules (`RencontrePublique`), le
// système suisse (`RencontreSuissePublique`) et l'arbre de duels (`DuelPublic`). L'onglet « En
// cours » les affiche tous ; écrire la ligne trois fois l'aurait fait diverger sur la seule chose
// qui compte — ce qu'un spectateur lit d'une rencontre.
//
// ⚠️ **Ce n'est pas un « remède structurel » au sens du CLAUDE.md**, et la distinction mérite d'être
// posée pour qu'on ne la confonde pas plus tard. Un remède structurel introduit un **pattern** sur
// preuve de 3ᵉ occurrence *déjà écrite*, et passe alors par un ADR et une US dédiée. Ici les deux
// occurrences supplémentaires n'existaient pas avant ce diff : la seule question était de les
// écrire une fois ou trois. Ne pas dupliquer ce qu'on écrit soi-même dans le même commit n'est pas
// une décision d'architecture, c'est le travail.
//
// ⚠️ **`DuellisteLisible` est redéclaré ici plutôt qu'importé** de `features/saisie-duels/api`. Un
// module de `shared/` qui importe d'une feature est l'inversion que `shared/salle/place.ts`
// documente comme la seule du front, et qu'elle a précisément corrigée : on ne la rouvre pas. Le
// typage structurel de TypeScript fait le reste — un `Duelliste` de feature satisfait ce contrat
// sans conversion. Le jour où `Duelliste` lui-même remontera en `shared/`, ce type-ci disparaîtra
// au profit du sien ; ce déménagement touche une demi-douzaine de features et n'a pas sa place dans
// une US de format.

/** Un duelliste, réduit à ce qu'une ligne de rencontre a besoin de nommer. */
export interface DuellisteLisible {
  archer_id: number
  nom: string
  prenom: string
}

/** La forme minimale d'une rencontre **rédigée**, commune aux trois formats.
 *
 * Volontairement pauvre : ni pavé, ni manches, ni validateur. La typer sur l'un des trois DTO
 * interdirait de la réutiliser sur les deux autres — même parti que `RondeLisible`
 * (`features/suisse/presentation.ts`), pour la même raison.
 *
 * `termine` et `validee` disent deux choses distinctes — le tir est allé au bout / le scoreur a
 * scellé —, et c'est **entre les deux** que le public lit « en attente de validation ».
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
 * ⚠️ Distinct d'`etatRencontre` (`features/suisse/presentation.ts`), qui lit le `duel` de saisie —
 * `validee_par`, `validation_en_attente`, `manches` — et ne peut donc pas servir ici : le DTO
 * public ne porte rien de tout cela, et c'est exactement sa raison d'être (règle 6).
 *
 * ⚠️ **Les deux vocabulaires se recouvrent sans être identiques**, et l'affirmation contraire a été
 * corrigée en revue (axe B). Là où la tablette distingue « à valider » de « validation en attente »
 * — deux états de **saisie** —, l'écran public n'en connaît qu'un, « en attente de validation », qui
 * les recouvre : le spectateur n'a pas à savoir laquelle des deux gâchettes manque. De même,
 * « tir mis de côté » est la forme courte de « tir mis de côté — population à rétablir », dont la
 * seconde moitié nomme un geste qui n'appartient qu'au scoreur. Ce n'est pas une divergence à
 * résorber, c'est une réduction voulue ; l'écrire « alignés » laissait croire à une contrainte
 * d'égalité que personne ne tient.
 *
 * `desynchronisee` passe en premier parce qu'elle **prime** : une rencontre dont le tir a été mis
 * de côté n'est pas « à tirer », elle est bloquée, et l'annoncer autrement ferait attendre des
 * archers pour rien (cf. la docstring du champ côté serveur).
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
