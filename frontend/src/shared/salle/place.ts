// Une **place de tir** dans la salle mise à plat : `[cible, couloir]`, le couloir étant une lettre
// (`A`…`D`).
//
// ⚠️ **Remonté ici en revue d'E05US030.** Le tuple vivait dans `features/poules/api.ts`, et
// `features/suisse` l'y importait — un saut feature → feature, que l'organisation par features
// (règle 10) réserve à `shared/`, et la **3ᵉ** occurrence du genre : c'est le seuil que le projet
// se fixe. `poules/api.ts` le ré-exporte, donc aucun import existant ne casse.
//
// ⚠️ **Homonymie à connaître** : `features/saisie-duels/api.ts` exporte une **autre** `Place` (une
// interface décrivant la place d'un duelliste sur un plan de duels, pas un couple cible/couloir).
// Les deux ne se distinguent aujourd'hui que par leur chemin d'import. Renommer l'une des deux
// demande de toucher les deux features et n'a pas sa place dans une US de format — c'est noté ici
// pour que la prochaine lecture ne les confonde pas.

/** Une place de tir : `[cible, couloir]` — le couloir est une lettre (`A`…`D`). */
export type Place = [number, string]
