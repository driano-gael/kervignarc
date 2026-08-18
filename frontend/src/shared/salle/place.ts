// Une **place de tir** dans la salle mise à plat : `[cible, couloir]`, le couloir étant une lettre
// (`A`…`D`).
//
// ⚠️ **Remonté ici en revue d'E05US030.** Le tuple vivait dans `features/poules/api.ts`, et
// `features/suisse` l'y importait — un saut feature → feature, que l'organisation par features
// (règle 10) réserve à `shared/`, et la **3ᵉ** occurrence du genre : c'est le seuil que le projet
// se fixe. `poules/api.ts` le ré-exporte, donc aucun import existant ne casse.
//
// ⚠️ **Ce qui remonte en `shared/`, c'est le VOCABULAIRE partagé, pas les surfaces.** La règle n'est
// pas « aucune feature n'importe d'une feature » : `features/phases` **orchestre** les formats et
// importe légitimement leurs hooks et leurs vues (`../poules/hooks`, `../suisse/hooks`,
// `../suisse/ClassementSuisse`). Ce qui n'a pas sa place dans une feature, c'est un **type que
// plusieurs features doivent nommer de la même façon** — précision ajoutée en revue, la première
// rédaction laissait croire à une règle appliquée à moitié dans le même commit.
//
// ⚠️ **Homonymie à connaître** : `features/saisie-duels/api.ts` exporte une **autre** `Place` (une
// interface décrivant la place d'un duelliste sur un plan de duels, pas un couple cible/couloir).
// Les deux ne se distinguent aujourd'hui que par leur chemin d'import. Renommer l'une des deux
// demande de toucher les deux features et n'a pas sa place dans une US de format — c'est noté ici
// pour que la prochaine lecture ne les confonde pas.

/** Une place de tir : `[cible, couloir]` — le couloir est une lettre (`A`…`D`). */
export type Place = [number, string]

/** Des places de tir en toutes lettres, **groupées par cible**.
 *
 * Un bloc de couloirs est contigu dans la salle *mise à plat*, pas sur une seule cible : une poule
 * de 6 en salle à 4 couloirs occupe `1C 1D 2A 2B 2C 2D`. La première version affichait « cible 1,
 * couloirs C, D, A, B, C, D » — deux « C » et deux « D » sur une cible qui n'en a que quatre — et le
 * cas n'a rien d'exotique, c'est le cas nominal dès qu'une poule ne tombe pas pile sur une cible
 * (relevé en revue d'E05US023). Le débordement est même ce que `_couloirs_du_gabarit` produit
 * *exprès*, en respectant des capacités qui peuvent varier d'une cible à l'autre.
 *
 * ⚠️ **Remontée ici en E05US031**, depuis `features/suisse/presentation.ts` où elle vivait seule.
 * L'onglet « En cours » la réclame pour les poules **et** pour le suisse ; l'importer depuis l'une
 * des deux features aurait rouvert l'inversion `shared/ → features/` que ce module documente
 * ci-dessus, et la recopier aurait été pire. `suisse/presentation.ts` la **ré-exporte**, donc aucun
 * import existant ne casse — même geste que `poules/api.ts` pour `Place`.
 *
 * ⚠️ **Une troisième copie vivait dans `features/poules/SaisiePoules.tsx`**, identique au caractère
 * près, et l'US ne l'avait pas vue alors qu'elle câblait `VuePoulesPublique` sur la version
 * partagée **dans le même répertoire** — relevé en revue (axes B et adversarial). Elle est
 * supprimée, et l'histoire du débordement ci-dessus **remonte avec la fonction** : c'est elle qui
 * rend le regroupement par cible relisible, et la laisser derrière aurait fait corriger un jour la
 * version partagée sans que l'écran de saisie en profite. */
export function decrirePlaces(places: readonly Place[]): string {
  const parCible = new Map<number, string[]>()
  for (const [cible, couloir] of places) {
    parCible.set(cible, [...(parCible.get(cible) ?? []), couloir])
  }
  return [...parCible.entries()]
    .map(([cible, couloirs]) => `cible ${cible} : ${couloirs.join(', ')}`)
    .join(' · ')
}
