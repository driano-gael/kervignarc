// Modèle de lecture du plan de cibles pour la **consultation publique** (E07US001, CA « plans de
// cibles »). Le DTO serveur `PlanDeCibles` porte des `archer_id` bruts ; la vue publique veut des
// **noms**. Cette fonction pure fait la jointure `archer_id → nom` et met le plan en forme d'affichage
// (cibles triées, positions triées), pour rester testable en node sans monter de composant.
//
// Elle ne touche **pas** à la réserve (`plan.conflits`) : un plan consultable montre *qui tire où*,
// pas la mécanique de placement (réserve, raisons de non-placement) qui reste l'affaire de l'admin
// (E03US004). Un archer non posé n'apparaît simplement sur aucune cible.

import type { PlanDeCibles } from './api'

// Un archer posé, prêt pour l'affichage : sa position (lettre « A »…« D ») et son nom résolu.
export interface PlaceConsultation {
  position: string
  nom: string
}

// Une cible du plan en lecture : son rang et les archers posés (triés par position). On ne porte
// **pas** la capacité : la vue publique n'affiche que « qui tire où » (numéro + occupants), pas le
// taux de remplissage — un champ non rendu n'a pas à traverser le modèle de lecture.
export interface CibleConsultation {
  index: number
  places: PlaceConsultation[]
}

// Construit la vue de consultation à partir du plan persisté et d'un annuaire `archer_id → nom`.
// Les cibles sont triées par `index` (l'ordre de la salle) et, dans chaque cible, les places par
// position (A avant B…). Un `archer_id` absent de l'annuaire (archer chargé en retard) retombe sur
// un libellé de repli plutôt que de disparaître — on préfère « Archer #12 » à une ligne muette.
export function construirePlanConsultation(
  plan: PlanDeCibles,
  nomParArcher: Map<number, string>,
): CibleConsultation[] {
  return [...plan.cibles]
    .sort((a, b) => a.index - b.index)
    .map((cible) => ({
      index: cible.index,
      places: [...cible.placements]
        .sort((a, b) => a.position.localeCompare(b.position))
        .map((placement) => ({
          position: placement.position,
          nom: nomParArcher.get(placement.archer_id) ?? `Archer #${placement.archer_id}`,
        })),
    }))
}
