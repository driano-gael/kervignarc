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
  detail: null,
  moment: null,
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
  // La cause chiffrée, telle que le serveur la rend — c'est la phrase du refus lui-même.
  detail: 'Ce tournoi ne peut pas démarrer : 28 archer(s) inscrit(s) pour 34 requis.',
  // Et **quand** ce refus tombera : les créneaux sont déjà là, seul l'effectif manque.
  moment: 'au démarrage',
}

// Ce que le serveur rend quand la question ne se pose plus : **aucune ligne**, et la raison. C'est
// lui qui le dit — l'écran ne déduit plus rien du statut (2ᵉ passe de revue, axe D).
const PLUS_RIEN_A_PREPARER: PreparationJalon = {
  jalon: 'demarrer',
  question: 'Prêt à démarrer ?',
  lignes: [],
  pret: false,
  bloquant: true,
  detail: 'Ce tournoi est déjà lancé : il n’y a plus rien à préparer avant son démarrage.',
  moment: null,
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
    monter(<PretADemarrer tournoiId={1} />)

    // Les créneaux **et** l'effectif : avec les seules gardes, l'organisateur n'aurait vu que le
    // refus « aucun départ », corrigé, recliqué, puis découvert l'effectif.
    expect(await screen.findByText('Créneaux')).toBeInTheDocument()
    expect(screen.getByText('Inscrits')).toBeInTheDocument()
    expect(screen.getByText('28/34')).toBeInTheDocument()
  })

  it('CA — répond d’abord à la question, en toutes lettres', async () => {
    vi.mocked(getPreparationJalon).mockResolvedValue(DEUX_MANQUES)
    monter(<PretADemarrer tournoiId={1} />)

    expect(await screen.findByRole('status')).toHaveTextContent('Pas encore')
  })

  it('CA — dit « oui » quand rien ne manque', async () => {
    monter(<PretADemarrer tournoiId={1} />)

    expect(await screen.findByRole('status')).toHaveTextContent('rien ne s’y oppose')
  })

  it('`D-15` — le bouton reste cliquable même quand rien n’est prêt', async () => {
    // **Le test qui compte.** Griser le bouton ferait décider une garde au front : il deviendrait
    // la seconde source que le CA interdit, et il divergerait du serveur au premier assouplissement
    // de la garde. E05US021 avait déjà tranché : on avertit avant, le serveur refuse au clic.
    vi.mocked(getPreparationJalon).mockResolvedValue(DEUX_MANQUES)
    vi.mocked(getTransitions).mockResolvedValue([VERS_PRET])
    monter(<PretADemarrer tournoiId={1} />)

    expect(await screen.findByRole('button', { name: 'Marquer prêt' })).toBeEnabled()
  })

  it('CA — porte l’action que le **serveur** offre, pas une action déduite du statut', async () => {
    // Depuis *brouillon*, l'étape suivante n'est pas « Démarrer » mais « Marquer prêt ». Tenir une
    // table locale des transitions aurait doublonné `domain.tournoi._TRANSITIONS` (ADR-0026 §2).
    vi.mocked(getTransitions).mockResolvedValue([VERS_PRET])
    monter(<PretADemarrer tournoiId={1} />)

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
    monter(<PretADemarrer tournoiId={1} />)

    await userEvent.click(await screen.findByRole('button', { name: 'Démarrer' }))

    await waitFor(() => expect(transitionnerTournoi).toHaveBeenCalledWith(1, 'demarrer'))
  })

  it('un tournoi déjà lancé ne propose plus de le préparer', async () => {
    // Sans ce cas, la rubrique resterait dans la sidebar toute la journée en offrant une action
    // qui n'a plus de sens — et le serveur répondrait 409 à qui la tenterait. Les deux versants
    // viennent du serveur : la raison (`detail`) et l'absence d'action (`transitions`).
    vi.mocked(getPreparationJalon).mockResolvedValue(PLUS_RIEN_A_PREPARER)
    vi.mocked(getTransitions).mockResolvedValue([])
    monter(<PretADemarrer tournoiId={1} />)

    expect(await screen.findByText(/déjà lancé/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Démarrer' })).toBeNull()
  })

  it('CA — dit **quand** le refus tombera, et le tient du serveur', async () => {
    // Depuis *brouillon*, l'action offerte est « Marquer prêt », qui n'exige que les créneaux : un
    // tournoi à 28/34 la passe sans broncher. « Ce qui manque sera refusé » se lisait donc comme un
    // refus **immédiat**, démenti par le clic suivant (1ʳᵉ passe de revue, axe D).
    //
    // ⚠️ Le moment vient de la **réponse**, il n'est pas écrit ici : les deux gardes ne tombent pas
    // au même clic, et l'écran l'ignorait en affichant « au démarrage » pour les deux — donc faux
    // pour les créneaux, sur l'état initial de tout tournoi neuf (2ᵉ passe, axe C1).
    vi.mocked(getPreparationJalon).mockResolvedValue(DEUX_MANQUES)
    vi.mocked(getTransitions).mockResolvedValue([VERS_PRET])
    monter(<PretADemarrer tournoiId={1} />)

    expect(await screen.findByRole('status')).toHaveTextContent('sera refusé au démarrage')
  })

  it('le moment suit la garde qui bloque en premier, pas le jalon', async () => {
    // Sans créneau, c'est `vers_pret` qui refuse — dès « Marquer prêt », pas au démarrage.
    vi.mocked(getPreparationJalon).mockResolvedValue({
      ...DEUX_MANQUES,
      moment: 'dès le passage en « prêt »',
    })
    vi.mocked(getTransitions).mockResolvedValue([VERS_PRET])
    monter(<PretADemarrer tournoiId={1} />)

    expect(await screen.findByRole('status')).toHaveTextContent(
      'sera refusé dès le passage en « prêt »',
    )
  })

  it('CA — chiffre la **cause** du blocage, pas seulement le manque', async () => {
    // `D-16` / `P-4` : une alerte qui ne chiffre pas son impact est un clic de plus, pas une
    // protection. Sur un tournoi à deux créneaux, « 8/34 » seul contredit le total affiché ailleurs
    // — la phrase du serveur nomme le créneau.
    vi.mocked(getPreparationJalon).mockResolvedValue(DEUX_MANQUES)
    monter(<PretADemarrer tournoiId={1} />)

    expect(
      await screen.findByText(/28 archer\(s\) inscrit\(s\) pour 34 requis/),
    ).toBeInTheDocument()
  })

  it('la question affichée vient du **serveur**, pas d’une table locale de libellés', async () => {
    // ADR-0096 §2. Le champ était rendu et jamais lu : l'ADR promettait une dérivation que le code
    // ne faisait pas, et le 3ᵉ membre aurait recopié un 3ᵉ littéral (relevé en revue par trois axes).
    vi.mocked(getPreparationJalon).mockResolvedValue({
      ...RIEN_NE_MANQUE,
      question: 'Prêt à décoller ?',
    })
    monter(<PretADemarrer tournoiId={1} />)

    expect(await screen.findByRole('heading', { name: 'Prêt à décoller ?' })).toBeInTheDocument()
  })

  it('un tournoi parti n’affiche ni verdict ni liste, et dit pourquoi', async () => {
    // L'écran affichait « Oui — rien ne s'y oppose » juste au-dessus de « ce tournoi est déjà
    // lancé », deux phrases qui se contredisent. La raison vient du **serveur** : l'écran ne sait
    // plus ce qu'est un statut, donc il ne peut plus se tromper dessus.
    vi.mocked(getPreparationJalon).mockResolvedValue(PLUS_RIEN_A_PREPARER)
    vi.mocked(getTransitions).mockResolvedValue([])
    monter(<PretADemarrer tournoiId={1} />)

    expect(await screen.findByText(/déjà lancé/)).toBeInTheDocument()
    expect(screen.queryByRole('status')).toBeNull()
    expect(screen.queryByText('Créneaux')).toBeNull()
  })

  it('la raison affichée est celle du serveur — un tournoi annulé n’est pas « déjà lancé »', async () => {
    // `_TRANSITIONS` autorise `brouillon → annule` : un tournoi annulé n'a jamais démarré. L'écran
    // tenait sa propre phrase pour ce cas ; c'est désormais le contrat qui la porte, donc
    // `E16US007` et `E16US008` en hériteront (2ᵉ passe de revue, quatre axes).
    vi.mocked(getPreparationJalon).mockResolvedValue({
      ...PLUS_RIEN_A_PREPARER,
      detail: 'Ce tournoi est annulé : il ne sera pas lancé.',
    })
    vi.mocked(getTransitions).mockResolvedValue([])
    monter(<PretADemarrer tournoiId={1} />)

    expect(await screen.findByText(/annulé/)).toBeInTheDocument()
    expect(screen.queryByText(/déjà lancé/)).toBeNull()
  })

  it('une lecture injoignable n’efface pas l’action (`P-3`)', async () => {
    // Même dégradation que `FriseCycleDeVie` et que l'écran jumeau : on dit qu'on n'a pas pu
    // vérifier, et on laisse passer. Le manque d'information ne verrouille jamais l'action.
    vi.mocked(getPreparationJalon).mockRejectedValue(new Error('LAN coupé'))
    monter(<PretADemarrer tournoiId={1} />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Préparation injoignable')
    expect(screen.getByRole('button', { name: 'Démarrer' })).toBeEnabled()
  })
})
