// Ce qu'une rencontre dit à **qui la saisit** — logique pure, aucun React (E05US027).
//
// Jumeau de `etatRencontre` (`shared/duels/rencontre.ts`), et volontairement **séparé de lui** :
// celui-là lit un DTO **public** (`termine`, `validee`, trois états), celui-ci lit le `duel` de
// saisie (`validee_par`, `validation_en_attente`, `manches`, six états). Les fondre reviendrait à
// faire circuler le contenu du tir vers les surfaces ouvertes, ce que la règle 6 interdit et ce que
// la scission des DTO existe pour empêcher.
//
// ## Pourquoi ce module existe, et pourquoi maintenant
//
// ⚠️ **C'est le rendez-vous posé par la revue d'E05US030**, et il est tenu à la lettre. La fonction
// était écrite **deux fois**, caractère pour caractère, dans `features/poules/SaisiePoules.tsx` et
// `features/suisse/presentation.ts`. Deux occurrences : « dupliquer une 2ᵉ fois et attendre le 3ᵉ
// cas » est la réponse que le § *Dette* de `CLAUDE.md` tient pour valide, donc rien n'avait été
// extrait — mais la fiche d'`E05US027` notait que sans rendez-vous écrit, la colline recopierait
// une **3ᵉ** fois par mimétisme et le seuil serait franchi sans que personne le remarque.
//
// La colline en a effectivement besoin. Le seuil est atteint **sur preuve dans le code du jour**,
// et l'extraction se fait ici plutôt qu'une troisième copie.
//
// ⚠️ **Ce n'est pas un « remède structurel » au sens du CLAUDE.md**, et la nuance est la même que
// celle que `rencontre.ts` pose déjà : on n'introduit aucun *pattern*, on déménage une fonction de
// huit lignes à l'endroit où ses trois appelants la voient. Pas d'ADR, pas d'US dédiée.
//
// ⚠️ **Aucun import depuis une feature.** `Duel` vit dans `features/saisie-duels/api`, et un module
// de `shared/` qui importerait d'une feature rouvrirait l'inversion que `shared/salle/place.ts`
// documente comme la seule du front — et qu'elle a précisément corrigée. Le contrat ci-dessous est
// donc **structurel** : un `Duel` de feature le satisfait sans conversion ni cast.

/** Ce qu'une rencontre en cours de saisie porte de son tir, réduit à ce que l'état lit. */
export interface DuelEnSaisie {
  /** Le nom du bénévole qui a scellé, ou `null`. C'est le sceau — il prime sur tout le reste. */
  validee_par: string | null
  /** Validation **mise en file hors-ligne** (E04US009), champ purement local : le serveur ne le
   * renvoie jamais. Seule la tablette qui a posé le geste le voit. */
  validation_en_attente?: boolean
  resultat?: { termine?: boolean } | null
  manches: readonly unknown[]
}

/** La forme minimale d'une rencontre **saisissable**, commune aux trois formats à rencontres. */
export interface RencontreEnSaisie {
  /** Un tir existe mais oppose d'autres duellistes : il est **masqué** et son écriture refusée
   * (ADR-0049 §4). Prime sur tout — la rencontre n'est pas « à tirer », elle est bloquée. */
  desynchronisee: boolean
  duel: DuelEnSaisie
}

/**
 * L'état d'une rencontre en un mot — le vocabulaire commun aux poules, au suisse et à la colline.
 *
 * L'ordre des tests **est** la règle, et chaque cran compte :
 *
 * 1. `desynchronisee` d'abord : une rencontre bloquée annoncée « à tirer » ferait attendre des
 *    archers devant une cible où le serveur refuse toute écriture ;
 * 2. `validee_par` — le sceau, définitif ;
 * 3. `validation_en_attente` — le geste est posé, c'est le **réseau** qu'on attend, pas une
 *    personne. Le confondre avec « à valider » enverrait réclamer un geste déjà fait ;
 * 4. `resultat.termine` — le tir est allé au bout, il reste à sceller ;
 * 5. `manches.length` — commencé, pas fini. ⚠️ **`resultat.termine` et non `manches.length > 0`
 *    pour « à valider »** : une rencontre à demi tirée est encore à saisir, et inverser les deux
 *    ferait proposer une validation que `Duel.valider` refuse (`DuelIncomplet`).
 */
export function etatRencontreDeSaisie(rencontre: RencontreEnSaisie): string {
  if (rencontre.desynchronisee) return 'tir mis de côté — population à rétablir'
  const duel = rencontre.duel
  if (duel.validee_par !== null) return 'validée'
  if (duel.validation_en_attente === true) return 'validation en attente'
  if (duel.resultat?.termine === true) return 'à valider'
  if (duel.manches.length > 0) return 'en cours'
  return 'à tirer'
}
