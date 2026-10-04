// Ce que montre une ligne de la grille du poste (`LigneArcher`, E17US011) — logique pure (E00US024).

import type { Bareme, Volee } from './api'
import { tamponDeVolee, type Brouillons } from './brouillons'
import type { Ouverture } from './poste'
import { cumulSaisi, totalVolee, voleeExistante, voleeOuverte, type PointsParZone } from './volees'

// Un score dont la règle (barème) ou la matière (série) n'est pas lue s'affiche « ? », jamais 0 :
// `pointsZone` n'a pas de défaut, un `{}` à la place de la table le contournerait.
export type Score = number | '?'

export function totalAffiche(valeurs: readonly string[], table: PointsParZone | null): Score {
  return table === null ? '?' : totalVolee(valeurs, table)
}

export interface EtatLigne {
  nbSaisies: Score
  cumul: Score
  // La volée ouverte, `null` tant que le barème n'est pas lu.
  numero: number | null
  enCours: readonly string[]
  verrouillee: boolean
  // La case marquée, `null` hors archer actif.
  caseEnCours: number | null
}

export function etatLigne(ligne: {
  archerId: number
  volees: readonly Volee[]
  serieLue: boolean
  bareme: Bareme | null
  brouillons: Brouillons
  // L'ouverture de `Saisie`, pour l'archer actif seulement.
  ouverture: Pick<Ouverture, 'numero' | 'fleche'> | null
  actif: boolean
}): EtatLigne {
  const { archerId, volees, serieLue, bareme, brouillons, ouverture, actif } = ligne
  const table = bareme?.points_par_zone ?? null
  // Par le **même** calcul que le pavé (`voleeOuverte`) : pour l'archer actif, la volée que le pavé
  // saisit ; pour les autres, leur prochaine à saisir.
  const numero =
    bareme === null ? null : voleeOuverte(ouverture?.numero ?? null, volees, bareme.nb_volees)
  const enCours = numero === null ? [] : tamponDeVolee(brouillons, archerId, numero, volees)
  return {
    nbSaisies: serieLue ? volees.length : '?',
    cumul: table === null || !serieLue ? '?' : cumulSaisi(volees, table),
    numero,
    enCours,
    verrouillee: numero !== null && (voleeExistante(volees, numero)?.verrouillee ?? false),
    // La flèche visée, sinon la prochaine à remplir — seulement sur l'archer actif.
    caseEnCours: actif ? (ouverture?.fleche ?? enCours.length) : null,
  }
}

// Le nom d'une case pour un lecteur d'écran : quatre archers ont chacun trois cases « 10 ».
export function libelleCase(index: number, nom: string, valeur: string | undefined): string {
  return `Flèche ${index + 1} de ${nom}${valeur === undefined ? '' : ` : ${valeur}`}`
}
