// Le libellé d'un créneau dans l'interface — **un seul**, partout.
//
// Depuis ADR-0075, plusieurs écrans désignent un départ (classement, forfaits, plan de cibles,
// pilotage du déroulé). Un « Départ 2 — 14:00 » ici et un « créneau n°2 » là, et l'organisateur ne
// sait plus s'il regarde le même. C'est de la donnée d'affichage, pas un composant : elle vit dans
// son propre module pour que `ChoixCreneau.tsx` n'exporte que son composant (règle `react-refresh`,
// qui perd le rafraîchissement à chaud d'un fichier mixte).

/** Ce qu'il faut savoir d'un départ pour le nommer — pas plus, pour rester utilisable partout. */
export interface CreneauChoisissable {
  id: number
  numero: number
  horaire: string | null
}

/** « Départ 2 — 14:00 », ou « Départ 2 » si l'horaire manque. */
export function libelleCreneau(depart: CreneauChoisissable): string {
  return `Départ ${depart.numero}${depart.horaire !== null ? ` — ${depart.horaire}` : ''}`
}
