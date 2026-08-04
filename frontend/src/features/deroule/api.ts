// Accès API de la feature « composer un déroulé » (E01US024, ADR-0063) : diagnostic d'un format
// (schéma à braquets + anomalies) et simulation sur N archers fictifs. Miroir des DTO de
// `api/v1/formats.py`.
//
// La feature ne redéclare **ni** `Etape` **ni** `FormatTournoi` : elle réutilise ceux de
// `features/patrimoine`, qui restent la source unique du modèle de format côté front. Ce qui est
// propre à cette US, c'est la **projection** — ce que le format produit, pas ce qu'il est.

import { fetchJson } from '../../shared/api/client'
import type { TypePhase } from '../../shared/phases/catalogue'
import type { Anomalie, Bloc } from '../../shared/schema-braquets/modele'

// Les types du **schéma** (blocs, flèches, braquets, anomalies) ont déménagé en
// `shared/schema-braquets/modele.ts` en E07US004, quand le pilotage et l'écran de salle sont devenus
// consommateurs du même dessin : un type partagé qui habite chez l'un de ses trois consommateurs
// ferait dépendre les deux autres d'une feature qui ne les concerne pas. Ils sont **ré-exportés**
// ici pour que les imports existants de la feature ne se disloquent pas.
export type { Anomalie, Bloc, Flux, Gravite, Tour } from '../../shared/schema-braquets/modele'

export interface Diagnostic {
  effectif: number | null
  applicable: boolean
  blocs: Bloc[]
  anomalies: Anomalie[]
  // E05US021 — le nombre d'inscrits en dessous duquel ce format ne peut pas se dérouler. Une
  // **donnée**, pas une anomalie : le cas « ce prélèvement ne prend personne » remonte déjà dans
  // `anomalies`, l'annoncer deux fois signalerait le même défaut sous deux formes.
  effectif_minimum: number
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
  // `false` quand le moteur ne sait pas dérouler ce type (poules, suisse, colline…) : ses chiffres
  // ne sont alors pas des constats, et l'écran doit le dire plutôt qu'afficher « — » comme un fait.
  joue: boolean
  tours: number
  tours_projetes: number | null
  duels: number
  duels_projetes: number | null
}

// Plafond d'effectif simulable — miroir d'`application/simulation_format.EFFECTIF_MAX`. Le serveur
// reste l'autorité (400) ; le front s'en sert seulement pour ne pas offrir un bouton voué au refus.
export const EFFECTIF_MAX = 200

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
