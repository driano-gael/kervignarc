// Formatage partagé de la feature « gabarits de salle ».

import type { Gabarit } from './api'

// Résumé d'un gabarit : nombre de cibles et plafond(s) d'archers observés.
// Ex. « 12 cibles · max 4 archer(s)/cible » ou « 4 cibles · plafonds 1/2/4 ».
export function decrire(gabarit: Gabarit): string {
  const plafonds = [...new Set(gabarit.cibles.map((cible) => cible.capacite))].sort((a, b) => a - b)
  const cibles = `${gabarit.nb_cibles} cible${gabarit.nb_cibles > 1 ? 's' : ''}`
  const plafond =
    plafonds.length === 1 ? `max ${plafonds[0]} archer(s)/cible` : `plafonds ${plafonds.join('/')}`
  return `${cibles} · ${plafond}`
}
