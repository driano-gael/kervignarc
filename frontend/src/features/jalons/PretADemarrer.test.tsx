// Tests de l'écran « **Prêt à démarrer ?** » (E16US012).
//
// Ce que ces tests gardent, et pourquoi ils montent le composant plutôt que d'appeler une fonction :
// le CA de l'US porte sur ce que l'organisateur **voit avant de cliquer**. La règle, elle, est déjà
// prouvée au domaine (`test_domain_jalon.py`) et l'accord avec les gardes au service
// (`test_service_jalons.py`) ; ce qui ne se lit qu'à l'écran, c'est :
//
//   - « il liste **ce qui manque** » — les deux manquements ensemble, pas l'un après l'autre ;
//   - « il **avertit sans bloquer** » (`D-15`) — le bouton reste cliquable même quand `pret` est
//     faux, parce que le refus appartient au serveur (arbitrage E05US021) ;
//   - « il porte **l'action** correspondante » — celle que le serveur offre, jamais une déduite du
//     statut (`useTransitions` est la source unique de la topologie, ADR-0026 §2).
//
// ⚠️ Le test « le bouton n'est pas grisé » est le plus important du fichier : c'est la seule chose
// qui empêche un futur correctif « d'ergonomie » de transformer cet écran en **seconde source** de
// garde, exactement ce que le CA « sans doublonner ce qui existe » interdit.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Transition } from '../accueil/api'
import { getTransitions, transitionnerTournoi } from '../accueil/api'
import type { PreparationJalon } from './api'
import { getPreparationJalon } from './api'
import { PretADemarrer } from './PretADemarrer'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getPreparationJalon: vi.fn(),
}))

vi.mock('../accueil/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../accueil/api')>()),
  getTransitions: vi.fn(),
  transitionnerTournoi: vi.fn(),
}))

// Fixture **typée** : un `vi.fn()` de factory ne l'est pas, et une fixture qui s'éloigne du DTO
// passerait `tsc` sans bruit — un champ manquant lu `undefined` prendrait la branche « tout va
// bien ». Même précaution que `completude/Completude.test.tsx`.
const RIEN_NE_MANQUE: PreparationJalon = {
  jalon: 'demarrer',
  question: 'Prêt à démarrer ?',
  lignes: [
    { cle: 'creneaux', libelle: 'Créneaux', etat: 'ok', fait: null, total: null },
    { cle: 'effectif', libelle: 'Inscrits', etat: 'ok', fait: 40, total: 34 },
    { cle: 'deroule', libelle: 'Déroulé composé', etat: 'ok', fait: null, total: null },
  ],
  pret: true,
  bloquant: true,
}

// Les **deux** gardes manquent en même temps : c'est le cas que les exceptions ne savaient pas
// rendre (elles s'arrêtent à la première).
const DEUX_MANQUES: PreparationJalon = {
  jalon: 'demarrer',
  question: 'Prêt à démarrer ?',
  lignes: [
    { cle: 'creneaux', libelle: 'Créneaux', etat: 'en_attente', fait: null, total: null },
    { cle: 'effectif', libelle: 'Inscrits', etat: 'alerte', fait: 28, total: 34 },
    { cle: 'deroule', libelle: 'Déroulé composé', etat: 'ok', fait: null, total: null },
  ],
  pret: false,
  bloquant: true,
}

const DEMARRER: Transition = { nom: 'demarrer', libelle: 'Démarrer', vers: 'en_cours' }
const VERS_PRET: Transition = { nom: 'vers-pret', libelle: 'Marquer prêt', vers: 'pret' }

function creerClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function monter(enfants: ReactNode) {
  return render(<QueryClientProvider client={creerClient()}>{enfants}</QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getPreparationJalon).mockResolvedValue(RIEN_NE_MANQUE)
  vi.mocked(getTransitions).mockResolvedValue([DEMARRER])
})

describe('Prêt à démarrer ?', () => {
  it('CA — liste **tous** les manquements d’un coup, pas le premier seulement', async () => {
    vi.mocked(getPreparationJalon).mockResolvedValue(DEUX_MANQUES)
    monter(<PretADemarrer tournoiId={1} statut="brouillon" />)

    // Les créneaux **et** l'effectif : avec les seules gardes, l'organisateur n'aurait vu que le
    // refus « aucun départ », corrigé, recliqué, puis découvert l'effectif.
    expect(await screen.findByText('Créneaux')).toBeInTheDocument()
    expect(screen.getByText('Inscrits')).toBeInTheDocument()
    expect(screen.getByText('28/34')).toBeInTheDocument()
  })

  it('CA — répond d’abord à la question, en toutes lettres', async () => {
    vi.mocked(getPreparationJalon).mockResolvedValue(DEUX_MANQUES)
    monter(<PretADemarrer tournoiId={1} statut="brouillon" />)

    expect(await screen.findByRole('status')).toHaveTextContent('Pas encore')
  })

  it('CA — dit « oui » quand rien ne manque', async () => {
    monter(<PretADemarrer tournoiId={1} statut="pret" />)

    expect(await screen.findByRole('status')).toHaveTextContent('rien ne s’y oppose')
  })

  it('`D-15` — le bouton reste cliquable même quand rien n’est prêt', async () => {
    // **Le test qui compte.** Griser le bouton ferait décider une garde au front : il deviendrait
    // la seconde source que le CA interdit, et il divergerait du serveur au premier assouplissement
    // de la garde. E05US021 avait déjà tranché : on avertit avant, le serveur refuse au clic.
    vi.mocked(getPreparationJalon).mockResolvedValue(DEUX_MANQUES)
    vi.mocked(getTransitions).mockResolvedValue([VERS_PRET])
    monter(<PretADemarrer tournoiId={1} statut="brouillon" />)

    expect(await screen.findByRole('button', { name: 'Marquer prêt' })).toBeEnabled()
  })

  it('CA — porte l’action que le **serveur** offre, pas une action déduite du statut', async () => {
    // Depuis *brouillon*, l'étape suivante n'est pas « Démarrer » mais « Marquer prêt ». Tenir une
    // table locale des transitions aurait doublonné `domain.tournoi._TRANSITIONS` (ADR-0026 §2).
    vi.mocked(getTransitions).mockResolvedValue([VERS_PRET])
    monter(<PretADemarrer tournoiId={1} statut="brouillon" />)

    expect(await screen.findByRole('button', { name: 'Marquer prêt' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Démarrer' })).toBeNull()
  })

  it('l’action déclenche la transition offerte', async () => {
    vi.mocked(transitionnerTournoi).mockResolvedValue({
      id: 1,
      nom: 'Tournoi',
      date: '2026-08-23',
      lieu: null,
      type_tournoi: 'officiel',
      statut: 'en_cours',
    })
    monter(<PretADemarrer tournoiId={1} statut="pret" />)

    await userEvent.click(await screen.findByRole('button', { name: 'Démarrer' }))

    await waitFor(() => expect(transitionnerTournoi).toHaveBeenCalledWith(1, 'demarrer'))
  })

  it('un tournoi déjà lancé ne propose plus de le préparer', async () => {
    // Sans ce cas, la rubrique resterait dans la sidebar toute la journée en offrant une action
    // qui n'a plus de sens — et le serveur répondrait 409 à qui la tenterait.
    monter(<PretADemarrer tournoiId={1} statut="en_cours" />)

    expect(await screen.findByText(/déjà lancé/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Démarrer' })).toBeNull()
  })

  it('une lecture injoignable n’efface pas l’action (`P-3`)', async () => {
    // Même dégradation que `FriseCycleDeVie` et que l'écran jumeau : on dit qu'on n'a pas pu
    // vérifier, et on laisse passer. Le manque d'information ne verrouille jamais l'action.
    vi.mocked(getPreparationJalon).mockRejectedValue(new Error('LAN coupé'))
    monter(<PretADemarrer tournoiId={1} statut="pret" />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Préparation injoignable')
    expect(screen.getByRole('button', { name: 'Démarrer' })).toBeEnabled()
  })
})
