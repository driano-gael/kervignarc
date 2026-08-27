// Une **place de tir** dans la salle mise à plat : `[cible, couloir]`, le couloir étant une lettre
// (`A`…`D`). `features/poules/api.ts` la ré-exporte.
//
// ⚠️ **Ce qui vit dans `shared/`, c'est le VOCABULAIRE partagé, pas les surfaces.** La règle n'est
// pas « aucune feature n'importe d'une feature » — `features/phases` orchestre les formats —, c'est
// qu'un **type que plusieurs features doivent nommer pareil** n'a pas sa place dans l'une d'elles.
// ⚠️ **Homonymie** : `features/saisie-duels/api.ts` exporte une **autre** `Place`, celle d'un
// duelliste sur un plan de duels. Les deux ne se distinguent que par leur chemin d'import.

/** Une place de tir : `[cible, couloir]` — le couloir est une lettre (`A`…`D`). */
export type Place = [number, string]

/** Des places de tir en toutes lettres, **groupées par cible**.
 *
 * ⚠️ Un bloc de couloirs est contigu dans la salle *mise à plat*, pas sur une seule cible : une
 * poule de 6 en salle à 4 couloirs occupe `1C 1D 2A 2B 2C 2D`. La première version affichait «
 * cible 1, couloirs C, D, A, B, C, D » — cas nominal dès qu'une poule ne tombe pas pile sur une
 * cible. Remontée ici en E05US031 : l'importer d'une feature aurait rouvert l'inversion `shared/ →
 * features/` que ce module documente ; `suisse/presentation.ts` la ré-exporte.
 */
export function decrirePlaces(places: readonly Place[]): string {
  const parCible = new Map<number, string[]>()
  for (const [cible, couloir] of places) {
    parCible.set(cible, [...(parCible.get(cible) ?? []), couloir])
  }
  return [...parCible.entries()]
    .map(([cible, couloirs]) => `cible ${cible} : ${couloirs.join(', ')}`)
    .join(' · ')
}
