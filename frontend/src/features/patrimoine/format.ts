// Mises en mots du patrimoine (E01US023) — fonctions **pures**, sans rendu.
//
// Séparées des `.tsx` pour la règle ESLint `react-refresh/only-export-components` (un fichier de
// composants n'exporte que des composants — même parti que `features/admin/axes.ts` et
// `features/gabarits/format.ts`), et parce qu'étant pures, elles se testent sans monter d'écran.

import { LIBELLE_TYPE } from '../../shared/phases/catalogue'
import type { Etape, RapportAssemblage } from './api'

/**
 * Rend le compte-rendu d'un assemblage lisible pour un organisateur.
 *
 * « Rien de neuf » plutôt qu'une suite de zéros : l'opération est **rejouable** (les briques déjà
 * présentes sont ignorées, jamais écrasées), et un rapport uniquement chiffré laisserait croire à
 * un échec là où il n'y a que du déjà-connu.
 */
export function decrireRapport(rapport: RapportAssemblage): string {
  const cree = rapport.categories_copiees + rapport.blasons_copies
  const ignore = rapport.categories_ignorees + rapport.blasons_ignores
  // Rien copié **et** rien ignoré : il n'y avait rien à copier. Dire « tout était déjà là » ici
  // serait faux et décourageant — c'est le cas de la toute première utilisation, avant tout
  // chargement du référentiel, et l'organisateur repartirait avec un tournoi vide en croyant
  // l'avoir garni.
  if (cree === 0 && ignore === 0) {
    return 'La bibliothèque du club est vide : chargez d’abord le référentiel FFTA depuis l’Atelier.'
  }
  if (cree === 0) return 'Rien de neuf : tout était déjà là.'
  return (
    `${rapport.categories_copiees} catégorie(s) et ${rapport.blasons_copies} blason(s) ajoutés ; ` +
    `${ignore} déjà présents, laissés tels quels.`
  )
}

/** Décrit une étape en langage d'organisateur (« Qualification 20×3 (16 archers) »). */
export function decrireEtape(etape: Etape): string {
  // E16US002 : le titre prime, le type reste lisible entre parenthèses — sans quoi la bibliothèque
  // décrivait « Élimination directe » pour une étape que l'organisateur avait nommée.
  const nom =
    etape.titre === null ? LIBELLE_TYPE[etape.type] : `${etape.titre} (${LIBELLE_TYPE[etape.type]})`
  const bareme =
    etape.bareme === null ? '' : ` ${etape.bareme.nb_volees}×${etape.bareme.nb_fleches_par_volee}`
  const effectif = etape.effectif === null ? '' : ` (${etape.effectif} archers)`
  return `${nom}${bareme}${effectif}`
}
