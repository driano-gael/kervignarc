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
 * ⚠️ **La règle de l'écran de salle ne se transpose pas ici** (correctif de 2ᵉ revue E01US025).
 * `departDeSalle` prend « le premier `lancé`, sinon le premier `ouvert` ». Or `EtatDepart` se dérive
 * de la **qualification seule** (`backend/domain/cycle_depart.py`) : un créneau passe `clos` quand
 * toutes ses séries sont closes, c'est-à-dire **à l'instant précis où ses duels commencent**. En
 * réutilisant la règle de salle, les écrans de duels désignaient donc le créneau *suivant* — celui
 * qui n'a pas encore tiré et n'a évidemment aucun tableau. Le seul créneau où il y avait des duels
 * à lancer était le seul qu'aucun des trois écrans n'affichait.
 *
 * La règle juste part du **dernier créneau clos** : sa qualification est finie, ce sont ses duels
 * qu'on joue. Elle reste correcte dans les trois moments de la journée, y compris le chevauchement
 * (duels du matin pendant la qualification de l'après-midi), où « le premier lancé » désignerait
 * l'après-midi alors que les duels sont ceux du matin :
 *
 * | Matin | Après-midi | Rendu | Duels réellement en cours |
 * |---|---|---|---|
 * | `lance` | `ouvert` | matin | matin (à venir) |
 * | `clos` | `lance` | matin | matin ✔ |
 * | `clos` | `clos` | après-midi | après-midi ✔ |
 *
 * Pure et testée, comme `departDeSalle` et pour la même raison : c'est une règle de choix, et trois
 * écrans doivent l'appliquer à l'identique.
 */
export function creneauDesDuels<T extends { etat: string }>(departs: readonly T[]): T | undefined {
  const clos = departs.filter((depart) => depart.etat === 'clos')
  return (
    clos[clos.length - 1] ??
    departs.find((depart) => depart.etat === 'lance') ??
    departs[departs.length - 1]
  )
}

/**
 * Le créneau **retenu** par un écran : le choix de l'utilisateur s'il est encore valide, sinon
 * celui qu'on est en train de tirer, sinon rien.
 *
 * ⚠️ **Le second filtre n'est pas cosmétique** (correctif de revue E01US025). Les trois écrans qui
 * portent un sélecteur de créneau (classement, forfaits de qualification, suivi du déroulé) gardent
 * leur choix dans un `useState` : supprimer ce créneau — ou changer de tournoi — laissait
 * `choixDepart` pointer un identifiant **disparu**, et l'écran continuait d'interroger le serveur
 * dessus. Selon la route, cela donne un 404 permanent ou, pire, une liste vide qui se lit comme
 * « rien à afficher ». Vérifier l'appartenance à la liste courante fait retomber proprement sur le
 * défaut.
 *
 * Fonction **pure**, à côté de `libelleCreneau` et pour la même raison : les trois écrans doivent
 * se comporter pareil, et c'est le genre de règle qu'on n'aligne pas en la recopiant.
 */
export function creneauRetenu<T extends { id: number }>(
  departs: readonly T[],
  choix: number | null,
  defaut: (departs: readonly T[]) => T | undefined,
): number | null {
  if (choix !== null && departs.some((depart) => depart.id === choix)) return choix
  return defaut(departs)?.id ?? null
}
