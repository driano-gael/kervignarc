// L'écran des inscriptions en « recherche d'abord, liste ensuite » (A09, variante B retenue le
// 04/08) — E17US007. Logique pure : ce qu'on liste, et les quatre compteurs d'entrée.

import type { Archer } from './api'

export type Filtre = 'tous' | 'non_places' | 'non_regles' | 'doublons'

// Les populations des compteurs, en identifiants d'archer. `null` = **inconnue** (lecture en échec
// ou impossible) : l'écran le dit, il ne l'affiche jamais comme un zéro.
export interface Ensembles {
  nonPlaces: ReadonlySet<number> | null
  nonRegles: ReadonlySet<number> | null
  doublons: ReadonlySet<number> | null
}

export interface Compteurs {
  inscrits: number
  nonPlaces: number | null
  nonRegles: number | null
  doublons: number | null
}

export interface Critere {
  requete: string
  filtre: Filtre | null
  // La fiche ouverte par l'adresse (E16US010, ADR-0100) : toujours listée.
  ouvert: number | null
}

// `DETTE-103` — 4ᵉ copie du repli casse + accents (variante de `suivi.ts`) : à extraire en `shared/`.
function normaliser(texte: string): string {
  return texte.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

function population(filtre: Filtre, ensembles: Ensembles): ReadonlySet<number> | 'tous' | null {
  if (filtre === 'tous') return 'tous'
  if (filtre === 'non_places') return ensembles.nonPlaces
  if (filtre === 'non_regles') return ensembles.nonRegles
  return ensembles.doublons
}

export function archersAffiches(
  archers: readonly Archer[],
  critere: Critere,
  ensembles: Ensembles,
): Archer[] {
  const q = normaliser(critere.requete)
  // « Recherche d'abord » : sans recherche ni compteur choisi, l'écran ne liste rien — sinon il
  // redevient la variante A, le tableau dense, que le questionnaire a écartée.
  const actif = q !== '' || critere.filtre !== null
  const cible = critere.filtre === null ? 'tous' : population(critere.filtre, ensembles)
  return archers.filter((a) => {
    if (a.id === critere.ouvert) return true
    if (!actif || cible === null) return false
    if (cible !== 'tous' && !cible.has(a.id)) return false
    return q === '' || normaliser(a.nom).includes(q) || normaliser(a.prenom).includes(q)
  })
}

export function compteurs(archers: readonly Archer[], ensembles: Ensembles): Compteurs {
  const parmi = (ensemble: ReadonlySet<number>) => archers.filter((a) => ensemble.has(a.id)).length
  return {
    inscrits: archers.length,
    nonPlaces: ensembles.nonPlaces === null ? null : parmi(ensembles.nonPlaces),
    nonRegles: ensembles.nonRegles === null ? null : parmi(ensembles.nonRegles),
    doublons: ensembles.doublons === null ? null : parmi(ensembles.doublons),
  }
}
