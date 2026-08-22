// Le **titre de phase** et la **fiche dépliable**, sur l'écran des phases d'un tournoi (E16US002).
//
// Tests dérivés du CA d'A07 (`stories/E16-retours-maquettes.md` → E16US002) : « *un écran liste les
// phases du tournoi, une ligne par phase* » et « *ouvrir une ligne ouvre la fiche de la phase — son
// **titre** et ses **réglages propres au type*** ».
//
// ⚠️ **Ce fichier monte `Phases` en entier, pas un contrôle isolé** — même parti que
// `Decoupage.test.tsx`, et pour la raison que son en-tête raconte : un test de formatage ne voit
// pas un défaut de câblage. Ce qu'on garde ici n'est pas « le champ sait s'afficher », c'est
// « l'organisateur peut nommer sa phase, quel qu'en soit le type ».
//
// ⚠️ **Les requêtes sont portées à la LIGNE** (`ligne()`), jamais à l'écran. L'écran monte en
// permanence un formulaire d'**ajout** qui porte les mêmes libellés que la fiche : une requête
// globale y matcherait le formulaire d'ajout et resterait verte avec la fiche entièrement décâblée.
// C'est le défaut latent que `Decoupage.test.tsx` portait, découvert en écrivant cette US.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import type { EtapeDeroule } from './api'
import { getPhases } from './api'
import { Phases } from './Phases'

vi.mock('./api', () => ({
  getPhases: vi.fn(),
  getAvancement: vi.fn(async () => []),
  ajouterPhase: vi.fn(),
  modifierPhase: vi.fn(),
  reordonnerPhases: vi.fn(),
  supprimerPhase: vi.fn(),
  changerStatutPhase: vi.fn(),
}))

const TABLEAU: EtapeDeroule = {
  id: 7,
  tournoi_id: 1,
  ordre: 1,
  type: 'elimination_directe',
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
  titre: null,
}

const QUALIFICATION: EtapeDeroule = {
  ...TABLEAU,
  id: 8,
  ordre: 1,
  type: 'qualification',
  nb_volees: 20,
}

function monter(phases: EtapeDeroule[]) {
  vi.mocked(getPhases).mockResolvedValue(phases)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<Phases tournoiId={1} />, { wrapper: Enveloppe })
}

function ligne(index = 0) {
  const element = screen.getAllByRole('listitem')[index]
  if (element === undefined) throw new Error(`Aucune ligne de phase au rang ${index}.`)
  return within(element)
}

async function ouvrirLaFiche(index = 0) {
  // ⚠️ **Le bouton se cherche DANS sa ligne, pas dans la liste globale.** Une fois une fiche
  // ouverte, son bouton devient « Fermer la fiche » : la liste des « Ouvrir la fiche » se décale,
  // et viser le n-ième élément de cette liste désigne la mauvaise ligne — ou aucune. Un premier
  // jet le faisait, et le clic partait dans le vide sans que l'assertion s'en aperçoive.
  await screen.findAllByRole('listitem')
  await userEvent.click(ligne(index).getByRole('button', { name: 'Ouvrir la fiche' }))
}

describe('le titre d’une phase', () => {
  it('remplace le libellé du type dans la liste quand il est renseigné', async () => {
    monter([{ ...TABLEAU, titre: 'Tableau des jeunes' }])

    expect(await screen.findByText('Tableau des jeunes')).toBeInTheDocument()
  })

  it('laisse le type tenir lieu de libellé quand il n’y en a pas', async () => {
    // Aucun déroulé existant n'a de titre : l'écran ne doit pas changer d'aspect pour eux.
    monter([TABLEAU])

    expect(await screen.findByText('Élimination directe')).toBeInTheDocument()
  })

  it('n’efface pas le type de la ligne : il devient un détail, il ne disparaît pas', async () => {
    // Sans lui, deux phases nommées ne diraient plus ce qu'elles **font** — et c'est justement
    // quand le déroulé porte plusieurs phases du même type que les titres servent.
    monter([{ ...TABLEAU, titre: 'Tableau des jeunes' }])
    await screen.findByText('Tableau des jeunes')

    expect(ligne().getByText(/Élimination directe/)).toBeInTheDocument()
  })

  it('distingue à l’œil deux phases de même type, ce qui est la raison d’être du champ', async () => {
    // Le CA voisin — « plusieurs phases de type qualification aux réglages différents » — a été
    // livré côté moteur par E05US024/E05US025. Sans titre, l'écran les rendait identiques : même
    // libellé de type, seul le rang pour les distinguer.
    monter([
      { ...QUALIFICATION, id: 1, ordre: 1, titre: 'Qualification jeunes' },
      { ...QUALIFICATION, id: 2, ordre: 2, titre: 'Qualification adultes' },
    ])

    expect(await screen.findByText('Qualification jeunes')).toBeInTheDocument()
    expect(screen.getByText('Qualification adultes')).toBeInTheDocument()
  })
})

describe('la fiche d’une phase', () => {
  it('est fermée au départ : la liste reste une liste', async () => {
    // C'est le fond du refus A07 — l'écran empilait tous les réglages à plat. Une liste de dix
    // phases qui déplierait tout serait le même mur, une US plus tard.
    monter([TABLEAU])
    await screen.findAllByRole('button', { name: 'Ouvrir la fiche' })

    expect(ligne().queryByLabelText(/Titre de la phase/)).not.toBeInTheDocument()
  })

  it('porte le titre et les réglages du type une fois ouverte', async () => {
    monter([TABLEAU])
    await ouvrirLaFiche()

    expect(ligne().getByLabelText(/Titre de la phase/)).toBeInTheDocument()
  })

  it('s’ouvre aussi sur la qualification, qui n’en avait aucune', async () => {
    // ⚠️ **Le cas qui portait le défaut.** La qualification est « gérée ailleurs » : elle n'ouvrait
    // aucun formulaire, et ses réglages traînaient à plat dans la barre d'actions. Elle était donc
    // le seul type impossible à nommer — précisément celui dont le CA dit qu'on peut en avoir
    // plusieurs.
    monter([QUALIFICATION])
    await ouvrirLaFiche()

    expect(ligne().getByLabelText(/Titre de la phase/)).toBeInTheDocument()
    expect(ligne().getByText(/Barrage jusqu.au rang/)).toBeInTheDocument()
  })

  it('n’ouvre que la fiche cliquée, pas celles des voisines', async () => {
    // Sans quoi « déplier une fiche » redeviendrait « déplier le mur », le refus d'origine.
    monter([
      { ...TABLEAU, id: 1, ordre: 1 },
      { ...TABLEAU, id: 2, ordre: 2 },
    ])
    await ouvrirLaFiche(0)

    expect(ligne(0).getByLabelText(/Titre de la phase/)).toBeInTheDocument()
    expect(ligne(1).queryByLabelText(/Titre de la phase/)).not.toBeInTheDocument()
  })
})
