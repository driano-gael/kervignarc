// Règles de zones du blason, côté client (E01US014) — fonctions **pures**, sans React.
//
// Ce sont des **miroirs** de règles qui vivent au domaine (`backend/domain/blason.py`) : le
// serveur reste l'autorité et revalide tout. Elles n'existent ici que pour éviter d'envoyer une
// requête vouée au 422 et pour rendre l'ordre d'affichage stable.
//
// Extraites du composant à dessein : inline dans `Blasons.tsx`, elles n'étaient testables qu'avec
// un rendu (le projet n'a ni jsdom ni testing-library). Ici, `vitest` seul suffit — même geste que
// pour `format.ts` (E00US014).

// Vocabulaire des zones de score en salle, du centre vers l'extérieur (référentiel FFTA §4.2).
// Miroir de l'énuméré `ZoneScore` du domaine ; sert aussi d'ordre d'affichage.
// Il vit ici, dans le module **pur**, et non dans `api.ts` (module HTTP) : c'est une règle, pas
// un détail de transport, et `zones.test.ts` n'a pas à charger le client HTTP pour l'exercer.
export const ZONES_CANONIQUES = ['10', '9', '8', '7', '6', '5', '4', '3', '2', '1', 'M'] as const

// Vocabulaire **fermé**, comme `TrancheAge` côté catégories : une valeur hors de cette liste est
// une erreur de compilation ici, et un 400 à la frontière serveur.
export type Zone = (typeof ZONES_CANONIQUES)[number]

export const ZONE_MANQUE: Zone = 'M'

// Zones par défaut à la création : le jeu complet d'un **blason simple**. Miroir de `ZONES_DEFAUT`
// du domaine, et **énuméré à part** de `ZONES_CANONIQUES` pour la même raison qu'au domaine : les
// deux coïncident aujourd'hui, mais ce sont deux concepts (le *vocabulaire* et le *jeu par
// défaut*). Réutiliser `ZONES_CANONIQUES` comme défaut ferait entrer en silence toute zone ajoutée
// au vocabulaire — X, si EPIC-06 le réclame — dans le pré-cochage de tout nouveau blason.
export const ZONES_DEFAUT: readonly Zone[] = [
  '10',
  '9',
  '8',
  '7',
  '6',
  '5',
  '4',
  '3',
  '2',
  '1',
  'M',
]

/** Coche ou décoche `zone`, en renvoyant toujours le jeu dans l'ordre canonique (10 → 1, puis M).
 *
 * L'ordre de saisie ne porte aucune information : le serveur normalise de toute façon, on lui
 * évite un aller-retour et on garde l'affichage stable pendant la saisie.
 */
export function basculerZone(actuelles: readonly Zone[], zone: Zone): Zone[] {
  const coche = !actuelles.includes(zone)
  // Une seule expression pour les deux sens : reconstruire depuis `ZONES_CANONIQUES` rend le
  // résultat canonique **par construction**. Un `filter` sur `actuelles` dans la branche décoche
  // se contenterait de préserver l'ordre reçu — la promesse ci-dessus ne tiendrait qu'à moitié.
  return ZONES_CANONIQUES.filter((z) => (z === zone ? coche : actuelles.includes(z)))
}

/** Vrai s'il reste au moins une zone **marquante** (autre que le manqué).
 *
 * Un blason sur lequel on ne peut rien marquer n'existe pas — le domaine le refuse.
 */
export function aUneZoneMarquante(zones: readonly Zone[]): boolean {
  return zones.some((zone) => zone !== ZONE_MANQUE)
}

/** Vrai si la case de `zone` doit être verrouillée (non décochable).
 *
 * Seul le manqué se verrouille — et **une fois coché seulement**. Le domaine impose `M` sur tout
 * blason : l'UI le verrouille plutôt que de laisser l'admin le décocher pour se faire refuser en
 * 422. Mais un blason qui arriverait **sans** `M` (base éditée à la main) doit rester rattrapable :
 * verrouiller inconditionnellement rendrait sa case ni cochée ni cochable, le PUT échouerait en
 * 422, et l'admin n'aurait aucune action dans l'UI pour s'en sortir — le blason deviendrait
 * inéditable, jusqu'à son nom.
 */
export function estVerrouillee(zones: readonly Zone[], zone: Zone): boolean {
  return zone === ZONE_MANQUE && zones.includes(ZONE_MANQUE)
}
