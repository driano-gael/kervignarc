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

/** Le créneau **dont on joue les duels** — et ce n'est pas celui de `departDeSalle`.
 *
 * ⚠️ **La règle de l'écran de salle ne se transpose pas ici.** `EtatDepart` se dérive de la
 * **qualification seule** : un créneau passe `clos` à l'instant où ses duels commencent, si bien
 * que « le premier lancé, sinon le premier ouvert » désignait le créneau *suivant* — le seul où il
 * y avait des duels était le seul qu'aucun écran n'affichait. La règle juste part du **dernier
 * créneau clos**, et reste correcte au chevauchement. Pure et testée : trois écrans l'appliquent.
 */
export function creneauDesDuels<T extends { etat: string }>(departs: readonly T[]): T | undefined {
  const clos = departs.filter((depart) => depart.etat === 'clos')
  return (
    clos[clos.length - 1] ??
    departs.find((depart) => depart.etat === 'lance') ??
    departs[departs.length - 1]
  )
}

/** Le créneau **retenu** par un écran : le choix de l'utilisateur s'il est encore valide, sinon
 * celui qu'on est en train de tirer, sinon rien.
 *
 * ⚠️ **Le second filtre n'est pas cosmétique** : les trois écrans à sélecteur gardent leur choix
 * dans un `useState`, et supprimer ce créneau — ou changer de tournoi — laissait `choixDepart`
 * pointer un identifiant **disparu**, donnant un 404 permanent ou, pire, une liste vide qui se lit
 * comme « rien à afficher ». Pure, comme `libelleCreneau` et pour la même raison.
 */
export function creneauRetenu<T extends { id: number }>(
  departs: readonly T[],
  choix: number | null,
  defaut: (departs: readonly T[]) => T | undefined,
): number | null {
  if (choix !== null && departs.some((depart) => depart.id === choix)) return choix
  return defaut(departs)?.id ?? null
}
