// Règles **pures** de la planche A17 · paiements (E17US012), testées sans rendu (`planche.test.ts`).

import type { Dette, LignePaiementArcher } from './api'

export interface TotauxDuBandeau {
  attendu_centimes: number
  encaisse_centimes: number
  restant_du_centimes: number
  archers_concernes: number
}

/** Le bandeau de la planche : attendu / encaissé / restant dû / archers concernés.
 *
 * « Concerné » = qui doit encore quelque chose (reste > 0) — la même population que celle qu'une
 * ancienneté date, côté serveur (`domain.paiement.dater_la_dette`).
 */
export function totauxDuBandeau(lignes: readonly LignePaiementArcher[]): TotauxDuBandeau {
  let attendu = 0
  let encaisse = 0
  let concernes = 0
  for (const { recap } of lignes) {
    attendu += recap.du_centimes
    encaisse += recap.paye_centimes
    if (recap.reste_centimes > 0) concernes += 1
  }
  return {
    attendu_centimes: attendu,
    encaisse_centimes: encaisse,
    restant_du_centimes: attendu - encaisse,
    archers_concernes: concernes,
  }
}

/** La colonne DEPUIS : « inscription du JJ/MM », « date inconnue », ou « — » sans dette.
 *
 * Jour et mois lus dans le fuseau **local** : l'instant est UTC, l'organisateur lit une date de
 * calendrier.
 */
export function libelleDepuis(dette: Dette | null): string {
  if (dette === null) return '—'
  if (dette.depuis === null) return 'date inconnue'
  const date = new Date(dette.depuis)
  const jour = String(date.getDate()).padStart(2, '0')
  const mois = String(date.getMonth() + 1).padStart(2, '0')
  return `inscription du ${jour}/${mois}`
}
