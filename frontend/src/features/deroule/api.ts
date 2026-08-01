// Accès API de la feature « composer un déroulé » (E01US024, ADR-0063) : diagnostic d'un format
// (schéma à braquets + anomalies) et simulation sur N archers fictifs. Miroir des DTO de
// `api/v1/formats.py`.
//
// La feature ne redéclare **ni** `Etape` **ni** `FormatTournoi` : elle réutilise ceux de
// `features/patrimoine`, qui restent la source unique du modèle de format côté front. Ce qui est
// propre à cette US, c'est la **projection** — ce que le format produit, pas ce qu'il est.

import { fetchJson } from '../../shared/api/client'
import type { NatureSource, TypePhase } from '../phases/api'
import type { IssueTour } from '../phases/api'

// Ce qu'une anomalie empêche (ADR-0063 §3). `bloquante` : le défaut est vrai quel que soit
// l'effectif, le format ne peut pas servir un tournoi. `avertissement` : il n'est vrai qu'à
// **cet** effectif — le format n'est pas faux, il ne tient pas ici.
export type Gravite = 'bloquante' | 'avertissement'

// Un défaut du déroulé, **localisé** : `ordre` désigne le bloc du schéma auquel le coller
// (`null` = la séquence entière). `code`/`message` viennent de l'erreur typée du domaine.
export interface Anomalie {
  code: string
  message: string
  ordre: number | null
  gravite: Gravite
}

// Une flèche du schéma : le même objet est la *sortie* du bloc amont et l'*entrée* du bloc aval.
export interface Flux {
  ordre_source: number
  ordre_cible: number
  nature: NatureSource
  effectif: number | null
  rang_debut: number | null
  rang_fin: number | null
  tour: number | null
  issue: IssueTour | null
}

// Un tour d'un tableau et son **braquet** : les rangs que se partagent gagnants et perdants
// (Règle R de `moteur-placement-lucky-loser.md`). Plages **absolues** (rangs du tournoi).
export interface Tour {
  tour: number
  duels: number
  plage_gagnants: [number, number]
  plage_perdants: [number, number]
}

// Un bloc du schéma — les quatre questions du CA : qui est là, ce qu'on leur demande, où ils vont
// après, combien de tours.
export interface Bloc {
  ordre: number
  type: TypePhase
  effectif: number | null
  tranche: [number, number] | null
  nb_volees: number | null
  nb_fleches_par_volee: number | null
  tours: Tour[]
  entrees: Flux[]
  sorties: Flux[]
  // Combien d'archers voient leur tournoi s'arrêter dans ce bloc. Ce n'est **pas** une anomalie :
  // les non-qualifiés gardent leur rang. Le CA demande que le dessin le montre, pas qu'il s'en
  // alarme.
  sans_suite: number | null
  anomalies: Anomalie[]
}

export interface Diagnostic {
  effectif: number | null
  applicable: boolean
  blocs: Bloc[]
  anomalies: Anomalie[]
}

export interface LigneClassement {
  rang: number | null
  nom: string
  prenom: string
  total: number
}

// Ce qu'une phase a réellement coûté. `ecart` vaut `true` quand le moteur n'a pas joué l'effectif
// que le schéma annonçait — aujourd'hui possible, cf. DETTE-028 (les duels ensemencent tous les
// archers en lice sans lire le prélèvement déclaré). L'afficher vaut mieux que servir un chiffre
// faux et muet à qui dimensionne ses scoreurs.
export interface PhaseSimulee {
  ordre: number
  type: TypePhase
  effectif: number
  effectif_projete: number | null
  ecart: boolean
  tours: number
  duels: number
}

export interface SimulationFormat {
  format_id: number
  nom: string
  effectif: number
  graine: number
  duels_total: number
  volees_total: number
  phases: PhaseSimulee[]
  classement: LigneClassement[]
  diagnostic: Diagnostic
}

// Lecture pure et **sans refus** : l'écran l'appelle sur un brouillon par définition incomplet, et
// le verdict est dans le corps (`applicable`), pas dans le code HTTP.
export function getDiagnostic(formatId: number, effectif: number | null): Promise<Diagnostic> {
  const suffixe = effectif === null ? '' : `?effectif=${effectif}`
  return fetchJson<Diagnostic>(`/api/v1/formats/${formatId}/diagnostic${suffixe}`)
}

export function simulerFormat(formatId: number, effectif: number): Promise<SimulationFormat> {
  return fetchJson<SimulationFormat>(`/api/v1/formats/${formatId}/simulation`, {
    method: 'POST',
    body: JSON.stringify({ effectif }),
  })
}
