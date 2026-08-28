// Tests de **montage** du schéma à braquets, sur le volet « où en est cette phase » (E05US032).
//
// Ce fichier naît d'un relevé de revue : la surface visible de l'US n'avait aucun test de rendu,
// alors que le composant est monté par **deux** surfaces. Le défaut le plus probable d'une ligne de
// ce genre est le **séparateur orphelin** quand le libellé est nul, et aucune porte mécanique ne le
// voit. Les deux premiers tests gardent le CA « le suivi montre le tour en cours de **chaque**
// phase démarrée » — au pluriel, ce qui est le point.

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { TypePhase } from '../phases/catalogue'
import { SchemaBraquets } from './SchemaBraquets'
import type { AvancementBloc, Bloc } from './modele'

function bloc(ordre: number, type: TypePhase, tours: Bloc['tours'] = []): Bloc {
  return {
    ordre,
    type,
    effectif: 8,
    tranche: null,
    nb_volees: null,
    nb_fleches_par_volee: null,
    tours,
    entrees: [],
    sorties: [],
    sans_suite: 0,
  }
}

function avancement(
  ordre: number,
  libelle: string | null,
  nb_tours = 5,
  tour_courant: number | null = 3,
): AvancementBloc {
  return {
    ordre,
    statut: 'en_cours',
    tour_courant,
    nb_tours,
    libelle_tour_courant: libelle,
    duels_joues: 0,
    duels_attendus: 0,
    tours: [],
  }
}

describe('le tour en cours des phases sans braquet', () => {
  it('annonce le tour dans le mot du format', () => {
    render(<SchemaBraquets blocs={[bloc(1, 'suisse')]} avancement={[avancement(1, 'Ronde 3')]} />)

    expect(screen.getByText(/Ronde 3/)).toBeInTheDocument()
  })

  it('annonce le tour de CHAQUE phase démarrée, pas seulement de la première', () => {
    // Le cœur du CA, et la raison pour laquelle la ligne vit dans ce composant plutôt que dans
    // l'en-tête du suivi : deux phases peuvent tourner en parallèle (poules sur une moitié de
    // salle, système suisse sur l'autre), et l'en-tête n'en nomme qu'une.
    render(
      <SchemaBraquets
        blocs={[bloc(1, 'poules'), bloc(2, 'suisse')]}
        avancement={[avancement(1, 'Tour 2'), avancement(2, 'Ronde 4')]}
      />,
    )

    expect(screen.getByText(/Tour 2/)).toBeInTheDocument()
    expect(screen.getByText(/Ronde 4/)).toBeInTheDocument()
  })

  it('n’imprime rien quand la phase n’annonce aucun tour', () => {
    // Une qualification, ou toute phase à un seul tour : le backend rend `null` et l'écran ne doit
    // pas afficher de marqueur orphelin (le « ▶ » seul, sans libellé derrière).
    render(<SchemaBraquets blocs={[bloc(1, 'qualification')]} avancement={[avancement(1, null)]} />)

    expect(screen.queryByText(/▶/)).not.toBeInTheDocument()
  })
})
