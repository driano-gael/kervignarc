// Présentation des équipes (E13US002) : libellés du type et des écarts de conformité.
// Séparé du `.tsx` pour la règle ESLint `react-refresh/only-export-components`.

import type { EcartEquipe, Equipe, TypeEquipe } from './api'

// Effectif FFTA par type (`stories/E13-equipes.md`, CA 1) : prérempli, modifiable par l'équipe.
export const TYPES_EQUIPE: Record<TypeEquipe, { libelle: string; effectifParDefaut: number }> = {
  standard: { libelle: 'Standard', effectifParDefaut: 3 },
  mixte: { libelle: 'Mixte', effectifParDefaut: 2 },
}

// `Record` exhaustif : un code d'écart ajouté à l'union ne compile pas sans son libellé.
const LIBELLES_ECART: Record<EcartEquipe, (equipe: Equipe) => string> = {
  effectif_insuffisant: (e) =>
    `Il manque des archers (${e.membres.length} sur ${e.effectif_attendu})`,
  effectif_excedentaire: (e) =>
    `Trop d’archers (${e.membres.length} pour ${e.effectif_attendu} attendus)`,
  armes_differentes: () => 'Armes différentes entre les membres',
  arme_non_verifiable: () => 'Arme non vérifiable : une catégorie n’a pas d’arme',
  mixite_manquante: () => 'Il faut un homme et une femme',
  sexes_differents: () => 'Sexes différents entre les membres',
  sexe_non_verifiable: () => 'Sexe non vérifiable : catégorie sans sexe ou mixte',
}

// ⚠️ Le serveur peut ajouter un code avant le front : jamais la valeur brute à l'écran.
export function libelleEcart(ecart: EcartEquipe, equipe: Equipe): string {
  const libelle = LIBELLES_ECART[ecart] as ((e: Equipe) => string) | undefined
  return libelle ? libelle(equipe) : 'Écart non reconnu'
}
