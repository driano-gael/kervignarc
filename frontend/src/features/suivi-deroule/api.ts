// Accès API du **suivi du déroulé** (E07US004, ADR-0064) : le schéma à braquets d'une édition en
// cours, rempli par la réalité. Miroir des DTO de `api/v1/suivi_deroule.py`.
//
// **Lecture publique** (portée `'aucune'`), et ce n'est pas un oubli : les deux consommateurs sont
// le poste de pilotage (admin, qui a un jeton) et l'**écran de salle**, qui n'en a pas — c'est un
// poste public projeté dans un gymnase. Un endpoint gardé rendrait l'écran muet.
//
// La feature ne redéclare **ni** `Bloc` **ni** `AvancementBloc` : ils viennent de
// `shared/schema-braquets/modele`, la source unique du modèle de schéma côté front.

import { fetchJson } from '../../shared/api/client'
import type { AvancementBloc, Bloc } from '../../shared/schema-braquets/modele'

export interface SuiviDeroule {
  /** Le nombre d'archers engagés — l'équivalent live du « je simule à N archers » de l'atelier. */
  effectif: number
  /** L'ordre de la phase qui tourne, ou `null` si aucune n'est démarrée. */
  ordre_courant: number | null
  /** Le **dessin** — exactement la forme que l'atelier reçoit de son diagnostic. */
  blocs: Bloc[]
  /** Le **remplissage**, apparié aux blocs par `ordre`. */
  avancement: AvancementBloc[]
}

export function getSuiviDeroule(tournoiId: number): Promise<SuiviDeroule> {
  return fetchJson<SuiviDeroule>(`/api/v1/tournois/${tournoiId}/suivi-deroule`, undefined, 'aucune')
}
