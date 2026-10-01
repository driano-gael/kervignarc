// Écran « Équipes » (E13US002, CA 1, 3, 4 et 8) — l'API est doublée au niveau du module `./api`.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ErreurApi } from '../../shared/api/client'
import type { Archer } from '../archers/api'
import type { EntreeEquipe, Equipe } from './api'
import { Equipes } from './Equipes'

const getEquipes = vi.fn()
const creerEquipe = vi.fn()
const modifierEquipe = vi.fn()
const supprimerEquipe = vi.fn()
const ajouterMembre = vi.fn()
const retirerMembre = vi.fn()
let equipesRendues: Equipe[] = []

vi.mock('./api', () => ({
  getEquipes: (t: number) => getEquipes(t),
  creerEquipe: (t: number, e: EntreeEquipe) => creerEquipe(t, e),
  modifierEquipe: (t: number, e: number, entree: EntreeEquipe) => modifierEquipe(t, e, entree),
  supprimerEquipe: (t: number, e: number) => supprimerEquipe(t, e),
  ajouterMembre: (t: number, e: number, a: number) => ajouterMembre(t, e, a),
  retirerMembre: (t: number, e: number, a: number) => retirerMembre(t, e, a),
}))

function archer(id: number, prenom: string, nom: string): Archer {
  return {
    id,
    tournoi_id: 1,
    nom,
    prenom,
    categorie_id: 10,
    cible: null,
    club_id: null,
    handicap_officiel: null,
    handicap_surcharge: null,
    handicap: 0,
    licence: null,
  }
}

const ARCHERS = [archer(1, 'Anne', 'Arc'), archer(2, 'Bruno', 'Bois'), archer(3, 'Chloé', 'Corde')]

vi.mock('../archers/api', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  getArchers: () => Promise.resolve(ARCHERS),
}))

vi.mock('../categories/api', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  getCategories: () => Promise.resolve([{ id: 10, libelle: 'Sénior arc classique homme' }]),
}))

// `staleTime` aligné sur la production (`app/queryClient.ts`) : à 0, le test du remontage serait
// vert quoi qu'il arrive.
function nouveauClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 30_000 } } })
}

function monter(client = nouveauClient()) {
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(<Equipes tournoiId={1} />, { wrapper: Enveloppe })
}

const aigles: Equipe = {
  id: 7,
  tournoi_id: 1,
  nom: 'Les Aigles',
  type: 'standard',
  effectif_attendu: 3,
  membres: [{ archer_id: 1, nom: 'Arc', prenom: 'Anne', categorie: 'Sénior arc classique femme' }],
  conforme: false,
  ecarts: ['effectif_insuffisant', 'sexe_non_verifiable'],
}

describe('Équipes', () => {
  beforeEach(() => {
    getEquipes.mockReset()
    getEquipes.mockImplementation(() => Promise.resolve(equipesRendues))
    creerEquipe.mockReset()
    modifierEquipe.mockReset()
    supprimerEquipe.mockReset()
    ajouterMembre.mockReset()
    retirerMembre.mockReset()
    equipesRendues = [aigles]
  })

  it('liste les équipes avec leurs écarts en clair, jamais le code brut', async () => {
    equipesRendues = [
      aigles,
      { ...aigles, id: 8, nom: 'Duo', type: 'mixte', conforme: true, ecarts: [] },
    ]
    monter()

    const ecarts = await screen.findByRole('list', { name: 'Écarts de l’équipe Les Aigles' })
    expect(within(ecarts).getByText('Il manque des archers (1 sur 3)')).toBeInTheDocument()
    expect(
      within(ecarts).getByText('Sexe non vérifiable : catégorie sans sexe ou mixte'),
    ).toBeInTheDocument()
    expect(screen.queryByText(/effectif_insuffisant|sexe_non_verifiable/)).toBeNull()
    expect(screen.getByText('CONFORME')).toBeInTheDocument()
  })

  it('préremplit l’effectif selon le type : 3 en standard, 2 en mixte', async () => {
    creerEquipe.mockResolvedValue(aigles)
    monter()
    const effectif = await screen.findByRole('spinbutton', { name: 'Effectif attendu' })
    expect(effectif).toHaveValue(3)

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Type d’équipe' }), 'mixte')
    expect(effectif).toHaveValue(2)

    await userEvent.type(screen.getByRole('textbox', { name: 'Nom de l’équipe' }), 'Duo')
    await userEvent.click(screen.getByRole('button', { name: 'Créer l’équipe' }))
    expect(creerEquipe).toHaveBeenCalledWith(1, { nom: 'Duo', type: 'mixte', effectif_attendu: 2 })
  })

  it('ajoute un membre choisi par recherche, une seule requête même au double-clic', async () => {
    // Promesse jamais résolue : la mutation reste en cours, le second clic doit trouver le bouton éteint.
    ajouterMembre.mockReturnValue(new Promise(() => {}))
    monter()
    await userEvent.click(
      await screen.findByRole('button', { name: 'Ajouter un membre à l’équipe Les Aigles' }),
    )
    await userEvent.type(screen.getByRole('searchbox', { name: /Rechercher un archer/ }), 'chlo')
    expect(screen.queryByRole('button', { name: /Ajouter Bruno Bois/ })).toBeNull()
    // Anne est déjà membre : elle n'est pas proposée.
    expect(screen.queryByRole('button', { name: /Ajouter Anne Arc/ })).toBeNull()

    const bouton = await screen.findByRole('button', {
      name: 'Ajouter Chloé Corde à l’équipe Les Aigles',
    })
    await userEvent.dblClick(bouton)
    expect(ajouterMembre).toHaveBeenCalledTimes(1)
    expect(ajouterMembre).toHaveBeenCalledWith(1, 7, 3)
    expect(bouton).toBeDisabled()
  })

  it('retire un membre en nommant l’archer et l’équipe', async () => {
    retirerMembre.mockResolvedValue({ ...aigles, membres: [] })
    monter()
    await userEvent.click(
      await screen.findByRole('button', { name: 'Retirer Anne Arc de l’équipe Les Aigles' }),
    )
    expect(retirerMembre).toHaveBeenCalledWith(1, 7, 1)
  })

  it('affiche tel quel le message du 409 « une équipe par type »', async () => {
    const message = 'Bruno Bois est déjà dans l’équipe standard « Les Faucons ».'
    ajouterMembre.mockRejectedValue(new ErreurApi(409, 'archer_deja_en_equipe', message))
    monter()
    await userEvent.click(
      await screen.findByRole('button', { name: 'Ajouter un membre à l’équipe Les Aigles' }),
    )
    await userEvent.click(
      await screen.findByRole('button', { name: 'Ajouter Bruno Bois à l’équipe Les Aigles' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
  })

  it('modifie une équipe : le PUT porte nom, type et effectif, puis la liste est relue', async () => {
    modifierEquipe.mockImplementation(() => {
      equipesRendues = [{ ...aigles, nom: 'Les Faucons', type: 'mixte', effectif_attendu: 2 }]
      return Promise.resolve(equipesRendues[0])
    })
    monter()
    await userEvent.click(
      await screen.findByRole('button', { name: 'Modifier l’équipe Les Aigles' }),
    )
    const formulaire = within(screen.getByRole('form', { name: 'Modifier l’équipe Les Aigles' }))
    const nom = formulaire.getByRole('textbox', { name: 'Nom de l’équipe' })
    await userEvent.clear(nom)
    await userEvent.type(nom, 'Les Faucons')
    await userEvent.selectOptions(
      formulaire.getByRole('combobox', { name: 'Type d’équipe' }),
      'mixte',
    )
    await userEvent.click(formulaire.getByRole('button', { name: 'Enregistrer' }))

    expect(modifierEquipe).toHaveBeenCalledWith(1, 7, {
      nom: 'Les Faucons',
      type: 'mixte',
      effectif_attendu: 2,
    })
    expect(await screen.findByText('Les Faucons')).toBeInTheDocument()
    expect(getEquipes).toHaveBeenCalledTimes(2)
  })

  it('supprime une équipe après confirmation, et sa ligne disparaît', async () => {
    supprimerEquipe.mockImplementation(() => {
      equipesRendues = []
      return Promise.resolve()
    })
    monter()
    await userEvent.click(
      await screen.findByRole('button', { name: 'Supprimer l’équipe Les Aigles' }),
    )
    expect(supprimerEquipe).not.toHaveBeenCalled()
    await userEvent.click(
      screen.getByRole('button', { name: 'Confirmer la suppression de l’équipe Les Aigles' }),
    )

    expect(supprimerEquipe).toHaveBeenCalledWith(1, 7)
    expect(await screen.findByText('Aucune équipe pour ce tournoi.')).toBeInTheDocument()
    expect(screen.queryByText('Les Aigles')).toBeNull()
  })

  it('relit la liste à chaque ouverture de l’écran, même avec un cache frais', async () => {
    const client = nouveauClient()
    const premier = monter(client)
    await screen.findByText('Les Aigles')
    premier.unmount()

    monter(client)
    await screen.findByText('Les Aigles')
    expect(getEquipes).toHaveBeenCalledTimes(2)
  })
})
