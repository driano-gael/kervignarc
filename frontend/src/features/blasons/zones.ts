// Règles de zones du blason, côté client (E01US014) — fonctions **pures**, sans React.
//
// Ce sont des **miroirs** de règles qui vivent au domaine (`backend/domain/blason.py`) : le
// serveur reste l'autorité et revalide tout. Elles n'existent ici que pour éviter d'envoyer une
// requête vouée au 422 et pour rendre l'ordre d'affichage stable.
//
// Extraites du composant à dessein : inline dans `Blasons.tsx`, elles n'étaient testables qu'avec
// un rendu (le projet n'a ni jsdom ni testing-library). Ici, `vitest` seul suffit — même geste que
// pour `format.ts` (E00US014).

import { ZONE_MANQUE, ZONES_CANONIQUES, type Zone } from './api'

/** Coche ou décoche `zone`, en renvoyant toujours le jeu dans l'ordre canonique (10 → 1, puis M).
 *
 * L'ordre de saisie ne porte aucune information : le serveur normalise de toute façon, on lui
 * évite un aller-retour et on garde l'affichage stable pendant la saisie.
 */
export function basculerZone(actuelles: readonly Zone[], zone: Zone): Zone[] {
  if (actuelles.includes(zone)) {
    return actuelles.filter((z) => z !== zone)
  }
  return ZONES_CANONIQUES.filter((z) => z === zone || actuelles.includes(z))
}

/** Vrai s'il reste au moins une zone **marquante** (autre que le manqué).
 *
 * Un blason sur lequel on ne peut rien marquer n'existe pas — le domaine le refuse.
 */
export function aUneZoneMarquante(zones: readonly Zone[]): boolean {
  return zones.some((zone) => zone !== ZONE_MANQUE)
}
