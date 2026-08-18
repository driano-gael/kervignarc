// Tests de **montage** de la vue publique du système suisse (E05US031, ADR-0089).
//
// ⚠️ **Écrits en correctif de revue** (axes B, C1 et C2) : l'US avait livré quatre composants de vue
// neufs et n'en montait qu'un. Les trois oubliés portaient précisément les deux CA les plus
// détaillés — la profondeur d'historique par format, et le filtre « mes archers ».
//
// Deux défauts réels ont été trouvés ici sans qu'aucun test ne puisse les voir, et les deux sont
// gardés ci-dessous : le porteur du **bye** échappait au filtre « mes archers », et les **conflits
// de pose** n'étaient pas annoncés alors que la vue des poules le fait, sur le même champ et dans
// le même onglet.
//
// Les cas dérivent de `docs/fonctionnel/E05US031.md` § scénarios 3 et 6, pas de l'implémentation.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EtatSuissePublique, RencontreSuissePublique, RondePublique } from './api'
import { getEtatSuisse } from './api'
import { VueSuissePublique } from './VueSuissePublique'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getEtatSuisse: vi.fn(),
}))

const MARTIN = { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' }
const DURAND = { archer_id: 2, nom: 'DURAND', prenom: 'Aline' }
const PETIT = { archer_id: 3, nom: 'PETIT', prenom: 'Jo' }

function rencontre(
  patch: Partial<RencontreSuissePublique> & Pick<RencontreSuissePublique, 'numero' | 'ronde'>,
): RencontreSuissePublique {
  return {
    couloirs: null,
    haut: MARTIN,
    bas: DURAND,
    points_haut: null,
    points_bas: null,
    vainqueur: null,
    termine: false,
    validee: false,
    desynchronisee: false,
    ...patch,
  }
}

function ronde(patch: Partial<RondePublique> & Pick<RondePublique, 'numero'>): RondePublique {
  return {
    rencontres: [rencontre({ numero: 1, ronde: patch.numero })],
    bye: null,
    close: false,
    ...patch,
  }
}

function etat(patch: Partial<EtatSuissePublique> = {}): EtatSuissePublique {
  return {
    phase_id: 9,
    nb_rondes: 3,
    rondes_maximales: 3,
    effectif: 3,
    rondes: [ronde({ numero: 1, close: true }), ronde({ numero: 2 })],
    classement: [],
    conflits: [],
    ...patch,
  }
}

function monter(noeud: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{noeud}</QueryClientProvider>)
}

beforeEach(() => vi.mocked(getEtatSuisse).mockReset())

describe('VueSuissePublique — la ronde qui se joue, et l’historique', () => {
  it('atterrit sur la première ronde non close', async () => {
    // CA du 18/08 : le suisse est le seul des trois formats à réclamer une navigation, parce qu'il
    // ré-apparie tout le plateau à chaque ronde — les afficher toutes noierait celle qu'on regarde.
    vi.mocked(getEtatSuisse).mockResolvedValue(etat())

    monter(<VueSuissePublique tournoiId={1} phaseId={9} />)

    expect(await screen.findByText(/Ronde 2 sur 3/)).toBeInTheDocument()
  })

  it('atterrit sur la dernière ronde quand toutes sont closes', async () => {
    // À 17 h tout est clos : un écran vide serait pire que la dernière ronde jouée.
    vi.mocked(getEtatSuisse).mockResolvedValue(
      etat({ rondes: [ronde({ numero: 1, close: true }), ronde({ numero: 2, close: true })] }),
    )

    monter(<VueSuissePublique tournoiId={1} phaseId={9} />)

    expect(await screen.findByText(/Ronde 2 sur 3/)).toBeInTheDocument()
  })

  it('laisse remonter aux rondes closes', async () => {
    vi.mocked(getEtatSuisse).mockResolvedValue(etat())

    monter(<VueSuissePublique tournoiId={1} phaseId={9} />)
    expect(await screen.findByText(/Ronde 2 sur 3/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Ronde 1' }))

    expect(await screen.findByText(/Ronde 1 sur 3/)).toBeInTheDocument()
  })

  it('n’explique l’attente que sous la ronde courante', async () => {
    // ⚠️ Garde du ⚠️ de la fiche (scénario 3-4) : la phrase « la ronde suivante sera appariée
    // une fois… » est vraie mais incompréhensible sous une ronde close consultée en historique.
    vi.mocked(getEtatSuisse).mockResolvedValue(etat())

    monter(<VueSuissePublique tournoiId={1} phaseId={9} />)
    expect(await screen.findByText(/sera appariée/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Ronde 1' }))

    expect(screen.queryByText(/sera appariée/)).toBeNull()
  })

  it('n’offre aucune barre de rondes sur l’écran projeté', async () => {
    // CA E07US004 : aucune interaction. Personne n'est là pour cliquer devant un projecteur.
    vi.mocked(getEtatSuisse).mockResolvedValue(etat())

    monter(<VueSuissePublique tournoiId={1} phaseId={9} interactif={false} />)

    expect(await screen.findByText(/Ronde 2 sur 3/)).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Rondes jouées' })).toBeNull()
  })
})

describe('VueSuissePublique — ce que l’écran nomme', () => {
  it('annonce le porteur du bye, qui marque sans tirer', async () => {
    // Le taire ferait chercher son nom dans une liste où il ne peut pas être.
    vi.mocked(getEtatSuisse).mockResolvedValue(etat({ rondes: [ronde({ numero: 1, bye: PETIT })] }))

    monter(<VueSuissePublique tournoiId={1} phaseId={9} />)

    expect(await screen.findByText(/Jo PETIT ne tire pas cette ronde/)).toBeInTheDocument()
  })

  it('annonce une ronde dont les cibles ne sont pas posées', async () => {
    // ⚠️ Correctif de revue (axe C1) : la vue des poules le faisait déjà, sur le même champ et dans
    // le même onglet, et le suisse se taisait — deux comportements à un écran d'écart.
    vi.mocked(getEtatSuisse).mockResolvedValue(
      etat({ conflits: [{ groupe: 2, raison: 'salle trop petite' }] }),
    )

    monter(<VueSuissePublique tournoiId={1} phaseId={9} />)

    expect(await screen.findByText(/n’a pas encore de cibles attribuées/)).toBeInTheDocument()
  })
})

describe('VueSuissePublique — « mes archers » (ADR-0079)', () => {
  it('cache le bye d’un archer qu’on ne suit pas', async () => {
    // ⚠️ **Défaut trouvé en revue (axes B et C1).** Le bloc du bye était rendu inconditionnellement :
    // en « mes archers », le nom d'un archer non suivi s'affichait quand même. Le CA dit que
    // l'interrupteur vaut ici « sans exception », et la fiche promet un filtrage des **lignes**.
    vi.mocked(getEtatSuisse).mockResolvedValue(etat({ rondes: [ronde({ numero: 1, bye: PETIT })] }))

    monter(<VueSuissePublique tournoiId={1} phaseId={9} mode="suivis" suivis={[1]} />)

    expect(await screen.findByText(/Ronde 1 sur 3/)).toBeInTheDocument()
    expect(screen.queryByText(/PETIT/)).toBeNull()
  })

  it('montre la ronde quand l’archer suivi porte justement le bye', async () => {
    // Le cas inverse, et il n'est pas symétrique : un archer suivi qui se repose reste engagé dans
    // la ronde. Répondre « aucun de vos archers ne tire ici » serait vrai à la lettre et faux au
    // fond — c'est ce que garde la condition composée de `BlocRonde`.
    vi.mocked(getEtatSuisse).mockResolvedValue(etat({ rondes: [ronde({ numero: 1, bye: PETIT })] }))

    monter(<VueSuissePublique tournoiId={1} phaseId={9} mode="suivis" suivis={[3]} />)

    expect(await screen.findByText(/Jo PETIT ne tire pas cette ronde/)).toBeInTheDocument()
    expect(screen.queryByText(/Aucun des archers que vous suivez/)).toBeNull()
  })

  it('nomme « aucun de vos archers ici » distinctement d’une ronde vide', async () => {
    vi.mocked(getEtatSuisse).mockResolvedValue(etat())

    monter(<VueSuissePublique tournoiId={1} phaseId={9} mode="suivis" suivis={[99]} />)

    expect(await screen.findByText(/Aucun des archers que vous suivez/)).toBeInTheDocument()
    expect(screen.queryByText(/aucune rencontre/)).toBeNull()
  })
})
