// Formatage partagé de la feature « gabarits de salle ».

import type { Gabarit } from './api'

// Résumé d'un gabarit : nombre de cibles et plafond(s) de couloirs de tir observés.
// Ex. « 12 cibles · jusqu'à 4 couloirs/cible » ou « 4 cibles · jusqu'à 1/2/4 couloirs/cible ».
//
// « jusqu'à » n'est pas décoratif : la capacité d'une cible est un **plafond**, pas un effectif.
// Le placement peut installer moins d'archers que de couloirs (un blason encombrant occupe la face
// entière) — l'affirmer comme une égalité tromperait sur ce que le gabarit garantit.
export function decrire(gabarit: Gabarit): string {
  const plafonds = [...new Set(gabarit.cibles.map((cible) => cible.capacite))].sort((a, b) => a - b)
  const cibles = `${gabarit.nb_cibles} cible${gabarit.nb_cibles > 1 ? 's' : ''}`
  // Accord sur le **plus grand** plafond, celui que porte le « jusqu'à » : « jusqu'à 1 couloir »,
  // mais « jusqu'à 1/2/4 couloirs ». La liste est triée, donc le dernier est le maximum.
  const maximum = plafonds[plafonds.length - 1] ?? 0
  const couloirs = `jusqu'à ${plafonds.join('/')} couloir${maximum > 1 ? 's' : ''}/cible`
  return `${cibles} · ${couloirs}`
}
