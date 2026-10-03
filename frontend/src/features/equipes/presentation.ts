// Présentation des équipes (E13US002) : libellés du type et des écarts de conformité.
// Séparé du `.tsx` pour la règle ESLint `react-refresh/only-export-components`.

import type { EcartEquipe, Equipe, TypeEquipe } from './api'

// Effectif FFTA par type (`stories/E13-equipes.md`, CA 1) : prérempli, modifiable par l'équipe.
// Miroir de `EFFECTIF_FFTA` (`backend/domain/equipe.py`).
export const TYPES_EQUIPE: Record<TypeEquipe, { libelle: string; effectifParDefaut: number }> = {
  standard: { libelle: 'Standard', effectifParDefaut: 3 },
  mixte: { libelle: 'Mixte', effectifParDefaut: 2 },
}

// `Record` exhaustif : un code d'écart ajouté à l'union ne compile pas sans son libellé.
const LIBELLES_ECART_COURTS: Record<EcartEquipe, string> = {
  effectif_insuffisant: 'Il manque des archers',
  effectif_excedentaire: 'Trop d’archers',
  armes_differentes: 'Armes différentes entre les membres',
  arme_non_verifiable: 'Arme non vérifiable : une catégorie n’a pas d’arme',
  mixite_manquante: 'Il faut un homme et une femme',
  sexes_differents: 'Sexes différents entre les membres',
  sexe_non_verifiable: 'Sexe non vérifiable : catégorie sans sexe ou mixte',
  blasons_differents: 'Blasons différents : les membres ne tirent pas sur le même blason',
  blason_non_verifiable: 'Blason non vérifiable : un membre n’a pas de blason connu',
}

const LIBELLES_ECART: Record<EcartEquipe, (equipe: Equipe) => string> = {
  effectif_insuffisant: (e) =>
    `Il manque des archers (${e.membres.length} sur ${e.effectif_attendu})`,
  effectif_excedentaire: (e) =>
    `Trop d’archers (${e.membres.length} pour ${e.effectif_attendu} attendus)`,
  armes_differentes: () => LIBELLES_ECART_COURTS.armes_differentes,
  arme_non_verifiable: () => LIBELLES_ECART_COURTS.arme_non_verifiable,
  mixite_manquante: () => LIBELLES_ECART_COURTS.mixite_manquante,
  sexes_differents: () => LIBELLES_ECART_COURTS.sexes_differents,
  sexe_non_verifiable: () => LIBELLES_ECART_COURTS.sexe_non_verifiable,
  blasons_differents: () => LIBELLES_ECART_COURTS.blasons_differents,
  blason_non_verifiable: () => LIBELLES_ECART_COURTS.blason_non_verifiable,
}

function estEcartConnu(ecart: string): ecart is EcartEquipe {
  return Object.hasOwn(LIBELLES_ECART_COURTS, ecart)
}

// Sans l'équipe sous la main (l'écran des duels, E13US004) : le libellé sans les effectifs.
export function libelleEcartCourt(ecart: string): string {
  return estEcartConnu(ecart) ? LIBELLES_ECART_COURTS[ecart] : 'Écart non reconnu'
}

// ⚠️ Le serveur peut ajouter un code avant le front : jamais la valeur brute à l'écran.
export function libelleEcart(ecart: EcartEquipe, equipe: Equipe): string {
  const libelle = LIBELLES_ECART[ecart] as ((e: Equipe) => string) | undefined
  return libelle ? libelle(equipe) : 'Écart non reconnu'
}
