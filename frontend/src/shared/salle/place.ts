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
