// Le **bouton de pose du plan de cibles** est monté pour CHAQUE type qui en a besoin (E05US027).
//
// ⚠️ **Ce fichier existe parce que le même défaut s'est produit trois fois.** Le hook, la route,
// le service et la table existaient à chaque fois ; ce qui manquait, c'était l'appelant :
//
//   1. E05US023 — `useRegenererPlanPoules` sans appelant, relevé en revue par deux axes ;
//   2. E05US030 — `PlanDeSuisse` écrit « d'emblée pour ne pas rejouer le défaut d'E05US023 » ;
//   3. E05US027 — `useRegenererPlanColline` sans appelant, relevé en revue. Le commentaire de
//      l'étape 2 n'a pas suffi : **un avertissement en prose ne se déclenche pas.**
//
// Le symptôme est le même les trois fois et il est grave : sans plan posé, tous les `couloirs`
// valent `null`, l'écran du scoreur réclame en boucle une action que l'application n'offre nulle
// part, et **personne ne sait sur quelle cible tirer**. Aucun test ne pouvait le voir : les tests
// de plan portaient sur le service et sur l'API, jamais sur le **montage**.
//
// D'où ce garde-fou, qui couvre les trois types d'un coup plutôt que le seul format du jour —
// sinon il ne ferait que déplacer le trou une quatrième fois. Un type à rencontres ajouté demain
// fera tomber le dernier cas s'il n'est pas monté.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { cleCollinePublique, clePoules, cleSuissePublique } from '../saisie-duels/hooks'
import type { EtapeDeroule } from './api'
import { getAvancement, getPhases } from './api'
import { Phases } from './Phases'

vi.mock('./api', () => ({
  getPhases: vi.fn(),
  getAvancement: vi.fn(),
  ajouterPhase: vi.fn(),
  modifierPhase: vi.fn(),
  reordonnerPhases: vi.fn(),
  supprimerPhase: vi.fn(),
  changerStatutPhase: vi.fn(),
}))

/** Une étape de déroulé au strict nécessaire : seul son `type` décide du bouton monté. */
function etape(
  id: number,
  type: EtapeDeroule['type'],
  reglage: Partial<EtapeDeroule>,
): EtapeDeroule {
  return {
    id,
    tournoi_id: 1,
    ordre: id,
    type,
    sources: [],
    effectif: null,
    barrage_jusqu_au: null,
    profondeur: null,
    poules: null,
    big_shoot_off: null,
    suisse: null,
    colline: null,
    decoupage: null,
    nb_volees: null,
    arrets: [],
    ...reglage,
  }
}

const PHASES = [
  etape(1, 'poules', {
    poules: {
      taille_visee: 4,
      bareme: null,
      nb_qualifies: 2,
      rencontres_par_archer: null,
      departage_inter_poules: false,
    },
  }),
  etape(2, 'suisse', { suisse: { nb_rondes: 5 } }),
  etape(3, 'colline', { colline: { nb_manches: 3, portee_de_defi: 1 } }),
]

/** Monte l'écran avec les trois états **déjà en cache**, plan non posé : c'est l'état d'une phase
 * fraîchement composée, donc celui où le bouton doit impérativement être offert. */
function poser(phases: EtapeDeroule[] = PHASES) {
  vi.mocked(getPhases).mockResolvedValue(phases)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(clePoules(1, 1), {
    phase_id: 1,
    poules: [],
    classement: [],
    conflits: [],
  })
  client.setQueryData(cleSuissePublique(1, 2), {
    phase_id: 2,
    nb_rondes: 5,
    rondes_maximales: 3,
    effectif: 4,
    rondes: [],
    classement: [],
    conflits: [],
  })
  client.setQueryData(cleCollinePublique(1, 3), {
    phase_id: 3,
    nb_manches: 3,
    portee_de_defi: 1,
    portee_maximale: 3,
    effectif: 4,
    manches: [],
    classement: [],
    conflits: [],
  })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<Phases tournoiId={1} />, { wrapper: Enveloppe })
}

describe('la pose du plan de cibles depuis l’écran des phases', () => {
  beforeEach(() => {
    vi.mocked(getPhases).mockResolvedValue(PHASES)
    vi.mocked(getAvancement).mockResolvedValue([])
  })

  it('offre le geste à CHAQUE type qui place ses archers par blocs', async () => {
    poser()

    // Un bouton par type à rencontres — poules, suisse, colline. Le compte est l'assertion : un
    // type monté en moins ne change pas le libellé, il change le nombre.
    const boutons = await screen.findAllByRole('button', { name: 'Générer le plan' })
    expect(boutons).toHaveLength(3)
  })

  it('offre le geste sur une colline SEULE, sans quoi le format est injouable', async () => {
    // Le cas d'E05US027 nommément, isolé : sur un déroulé qui n'a QUE la colline, l'échec dit
    // lequel des trois types manque, là où le compte ci-dessus dirait seulement « 2 au lieu de 3 ».
    poser([PHASES[2]!])

    expect(await screen.findAllByRole('button', { name: 'Générer le plan' })).toHaveLength(1)
  })
})
