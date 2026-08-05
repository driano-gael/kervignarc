// Formatage partagé de la feature « gabarits de salle ».

import type { Gabarit } from './api'

// Résumé d'un gabarit : nombre de cibles et nombre(s) de couloirs de tir observés.
// Ex. « 12 cibles · 4 couloirs/cible » ou « 4 cibles · 1/2/4 couloirs/cible ».
export function decrire(gabarit: Gabarit): string {
  const plafonds = [...new Set(gabarit.cibles.map((cible) => cible.capacite))].sort((a, b) => a - b)
  const cibles = `${gabarit.nb_cibles} cible${gabarit.nb_cibles > 1 ? 's' : ''}`
  const couloirs = `${plafonds.join('/')} couloir${plafonds.length > 1 || plafonds[0] !== 1 ? 's' : ''}/cible`
  return `${cibles} · ${couloirs}`
}
