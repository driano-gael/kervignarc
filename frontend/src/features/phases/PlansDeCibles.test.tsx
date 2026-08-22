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
// sinon il ne ferait que déplacer le trou une quatrième fois.
//
// ⚠️ **Et il itère sur `TYPES_A_PLAN_PAR_BLOCS`, ce qui n'est pas un détail de style.** Une
// première rédaction posait un décor de trois types **en dur** tout en promettant, par écrit,
// qu'« un type ajouté demain fera tomber le dernier cas ». C'était faux : le décor ne contenait pas
// le type ajouté, donc le test restait vert — une **fausse assurance**, à l'endroit exact où le
// prochain implémenteur irait vérifier s'il doit se méfier. Pire que le commentaire en prose qui
// avait déjà échoué, puisque celle-là se présentait comme un test (relevé par l'axe adversarial en
// 2ᵉ passe, sur le correctif d'un bloquant de 1ʳᵉ passe).
//
// En dérivant décor **et** montage de la même table, un type qui y entre sans panneau fait
// réellement rougir. Ce que ce test ne peut toujours pas voir : un type qui gagne un plan par blocs
// côté **serveur** sans être ajouté à la table front — rien ne compare mécaniquement les deux, et
// c'est dit ici plutôt que promis.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TYPES_A_PLAN_PAR_BLOCS, type TypePhase } from '../../shared/phases/catalogue'
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

/** Un décor par type de `TYPES_A_PLAN_PAR_BLOCS` — **et le test échoue si l'un manque**.
 *
 * C'est la moitié qui rend la promesse de l'en-tête vraie : ajouter un type à la table sans lui
 * donner ni décor ni panneau fait tomber `chaque type de la table a son décor` ci-dessous, avant
 * même d'arriver aux assertions de rendu. Sans ce contrôle, un type non décrit ici serait
 * silencieusement absent du décor, donc jamais testé — le trou se rouvrirait par le décor.
 */
const DECORS: Partial<Record<TypePhase, Partial<EtapeDeroule>>> = {
  poules: {
    poules: {
      taille_visee: 4,
      bareme: null,
      nb_qualifies: 2,
      rencontres_par_archer: null,
      departage_inter_poules: false,
    },
  },
  suisse: { suisse: { nb_rondes: 5 } },
  colline: { colline: { nb_manches: 3, portee_de_defi: 1 } },
}

const TYPES = [...TYPES_A_PLAN_PAR_BLOCS]
const PHASES = TYPES.map((type, index) => etape(index + 1, type, DECORS[type] ?? {}))

/** Monte l'écran avec les trois états **déjà en cache**, plan non posé : c'est l'état d'une phase
 * fraîchement composée, donc celui où le bouton doit impérativement être offert. */
/** L'entrée de cache d'un type, à l'`id` de sa phase — plan **non posé**, donc bouton dû. */
function amorcer(client: QueryClient, type: TypePhase, id: number) {
  const commun = { phase_id: id, classement: [], conflits: [] }
  if (type === 'poules') client.setQueryData(clePoules(1, id), { ...commun, poules: [] })
  if (type === 'suisse')
    client.setQueryData(cleSuissePublique(1, id), {
      ...commun,
      nb_rondes: 5,
      rondes_maximales: 3,
      effectif: 4,
      rondes: [],
    })
  if (type === 'colline')
    client.setQueryData(cleCollinePublique(1, id), {
      ...commun,
      nb_manches: 3,
      portee_de_defi: 1,
      portee_maximale: 3,
      effectif: 4,
      manches: [],
    })
}

function poser(phases: EtapeDeroule[] = PHASES) {
  vi.mocked(getPhases).mockResolvedValue(phases)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  phases.forEach((phase) => amorcer(client, phase.type, phase.id))
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

  it('a un décor pour chaque type de la table — sinon le trou se rouvre par le décor', () => {
    // Contrôle préalable, et il compte autant que les suivants : un type ajouté à
    // `TYPES_A_PLAN_PAR_BLOCS` sans décor ici serait rendu sans réglage, donc potentiellement sans
    // bouton, sans que personne ne sache pourquoi.
    expect(TYPES.filter((type) => DECORS[type] === undefined)).toEqual([])
  })

  it('offre le geste à CHAQUE type qui place ses archers par blocs', async () => {
    poser()

    const boutons = await screen.findAllByRole('button', { name: 'Générer le plan' })
    expect(boutons).toHaveLength(TYPES.length)
  })

  it.each(TYPES)(
    'offre le geste sur une phase de type %s SEULE, sans quoi le format est injouable',
    async (type) => {
      // Chaque type isolé : l'échec dit **lequel** manque, là où le compte ci-dessus dirait
      // seulement « 2 au lieu de 3 ». C'est ce cas-ci qu'un type neuf non monté fera tomber.
      const seule = PHASES.find((phase) => phase.type === type)!
      poser([seule])

      expect(await screen.findAllByRole('button', { name: 'Générer le plan' })).toHaveLength(1)
    },
  )
})
