// Ce qu'une rencontre dit à **qui la saisit** — logique pure, aucun React.
//
// ⚠️ **Jumeau de `etatRencontre` (`shared/duels/rencontre.ts`), et volontairement SÉPARÉ** :
// celui-là lit un DTO **public** (trois états), celui-ci le `duel` de saisie (six états). Les
// fondre ferait circuler le contenu du tir vers les surfaces ouvertes (règle 6). ⚠️ **Aucun import
// depuis une feature** : un module de `shared/` qui importerait d'une feature rouvrirait
// l'inversion que `shared/salle/place.ts` documente. Le contrat est donc **structurel** — un `Duel`
// de feature le satisfait sans conversion ni cast.

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
 * ⚠️ **L'ordre des tests EST la règle** : `desynchronisee` d'abord (une rencontre bloquée annoncée
 * « à tirer » ferait attendre des archers), `validee_par`, `validation_en_attente` (le geste est
 * posé, c'est le **réseau** qu'on attend), `resultat.termine`, puis `manches.length`. ⚠️ Et non
 * `manches.length > 0` pour « à valider » : une rencontre à demi tirée est encore à saisir.
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
