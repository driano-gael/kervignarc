// Règles d'affichage **pures** du suivi des paiements (E08US002), extraites de `Paiements.tsx` pour
// être testables sans monter de composant (convention front : les petites règles vivent dans un
// helper pur, testé — cf. `competition/format.ts`, `saisie/volees.ts`).
//
// Deux dérivations depuis un récapitulatif dû/payé/reste :
//  - le **statut** affiché (pastille) ;
//  - l'**action** de règlement groupé proposée (bouton), ou `null` s'il n'y a rien à régler.

import type { RecapPaiement } from './api'

// Rien à payer (dû 0) → « neutre » ; tout réglé (reste 0) → « regle » ; une partie payée → « partiel » ;
// rien payé → « du ». L'ordre des tests compte : `reste 0` avant `payé > 0` (tout payé n'est pas partiel).
export type StatutPaiement = 'neutre' | 'regle' | 'partiel' | 'du'

export function statutPaiement(recap: RecapPaiement): StatutPaiement {
  if (recap.du_centimes === 0) return 'neutre'
  if (recap.reste_centimes === 0) return 'regle'
  if (recap.paye_centimes > 0) return 'partiel'
  return 'du'
}

// Action du bouton de règlement groupé : « regler » (il reste à payer), « annuler » (tout est payé,
// on peut revenir en arrière), ou `null` (le périmètre ne doit rien — pas de bouton).
export type ActionMarquage = 'regler' | 'annuler' | null

export function actionMarquage(recap: RecapPaiement): ActionMarquage {
  if (recap.du_centimes === 0) return null
  return recap.reste_centimes > 0 ? 'regler' : 'annuler'
}
