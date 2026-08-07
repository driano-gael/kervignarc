// Tests de **placement** de la complétude (E16US003) — le sportif au pilotage, l'administratif à la
// gestion, depuis une seule source.
//
// Pourquoi des tests de rendu et pas de logique pure : le CA d'E16US003 ne porte sur aucun calcul.
// Le serveur sépare déjà `sportif` et `hors_sportif` (E12US005), et `presentation.test.ts` couvre
// déjà la dérivation. Ce que l'US décide, c'est **où chaque liste s'affiche** — un fait qui ne se
// lit qu'en montant les composants. `tsc` et `eslint` ne voient rien d'une section rendue au mauvais
// endroit, et le refus d'A14 portait précisément là-dessus.
//
// Les cas se lisent depuis le CA de `stories/E16-retours-maquettes.md` :
//   - « deux écrans, une source » : le sportif ici, l'administratif là, **sans dupliquer le calcul** ;
//   - « le bouton "Terminer" suit le sportif ».
// Les assertions **négatives** (`queryBy… toBeNull`) sont le cœur du fichier : c'est le mélange qui
// était refusé, donc c'est l'absence qu'il faut prouver — un test qui ne vérifierait que la présence
// resterait vert si les deux sections revenaient sur le même écran.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Completude as CompletudeDTO } from './api'
import { getCompletude } from './api'
import { Completude } from './Completude'
import { CompletudeAdministrative } from './CompletudeAdministrative'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getCompletude: vi.fn(),
}))

function reponse(): CompletudeDTO {
  return {
    sportif: [
      { cle: 'qualification', libelle: 'Qualification', etat: 'alerte', fait: 28, total: 30 },
      {
        cle: 'phases_eliminatoires',
        libelle: 'Phases éliminatoires',
        etat: 'a_venir',
        fait: null,
        total: null,
      },
      { cle: 'classement', libelle: 'Classement', etat: 'en_attente', fait: null, total: null },
    ],
    hors_sportif: [
      { cle: 'paiements', libelle: 'Paiements', etat: 'alerte', fait: 113, total: 120 },
    ],
    sportif_complet: false,
  }
}

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

describe('CA E16US003 — le pilotage ne montre que le déroulé', () => {
  beforeEach(() => {
    vi.mocked(getCompletude).mockResolvedValue(reponse())
  })

  it('rend les lignes sportives', async () => {
    render(<Cadre enfants={<Completude tournoiId={1} statut="en_cours" />} />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    expect(screen.getByText('Classement')).toBeInTheDocument()
    expect(screen.getByText('28/30 cibles')).toBeInTheDocument()
  })

  it('ne rend AUCUNE ligne administrative — c’est le refus d’A14', async () => {
    render(<Cadre enfants={<Completude tournoiId={1} statut="en_cours" />} />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    // Ni la ligne, ni le titre de section qui la portait.
    expect(screen.queryByText('Paiements')).toBeNull()
    expect(screen.queryByText('Hors sportif')).toBeNull()
    expect(screen.queryByText('113/120')).toBeNull()
  })

  it('CA — le bouton « Terminer » reste du côté déroulé', async () => {
    render(<Cadre enfants={<Completude tournoiId={1} statut="en_cours" />} />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Terminer le tournoi' })).toBeInTheDocument()
  })
})

describe('CA E16US003 — la gestion porte la complétude administrative', () => {
  beforeEach(() => {
    vi.mocked(getCompletude).mockResolvedValue(reponse())
  })

  it('rend la ligne administrative et son décompte d’archers', async () => {
    render(<Cadre enfants={<CompletudeAdministrative tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByText('Paiements')).toBeInTheDocument())
    // Décompte **nu** (pas de suffixe « cibles ») : ce sont des archers réglés, pas des cibles.
    expect(screen.getByText('113/120')).toBeInTheDocument()
    expect(screen.getByText('Complétude administrative')).toBeInTheDocument()
  })

  it('ne rend AUCUNE ligne sportive, ni le bouton « Terminer »', async () => {
    render(<Cadre enfants={<CompletudeAdministrative tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByText('Paiements')).toBeInTheDocument())
    expect(screen.queryByText('Qualification')).toBeNull()
    expect(screen.queryByText('Classement')).toBeNull()
    // Terminer fige le sportif : le proposer depuis un écran de gestion rejouerait le mélange.
    expect(screen.queryByRole('button', { name: 'Terminer le tournoi' })).toBeNull()
  })

  it('CA « une source » — les deux écrans lisent le MÊME appel, rien n’est recalculé', async () => {
    // Le garde-fou du CA : si un jour quelqu'un ajoutait un endpoint « complétude administrative »,
    // ce test tomberait. La séparation est une affaire de destination, pas de calcul.
    render(<Cadre enfants={<CompletudeAdministrative tournoiId={7} />} />)

    await waitFor(() => expect(screen.getByText('Paiements')).toBeInTheDocument())
    expect(getCompletude).toHaveBeenCalledWith(7)
  })

  it('dit l’erreur sans masquer l’écran des paiements qui l’héberge', async () => {
    vi.mocked(getCompletude).mockRejectedValue(new Error('réseau coupé'))

    render(<Cadre enfants={<CompletudeAdministrative tournoiId={1} />} />)

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent('réseau coupé')
  })
})
