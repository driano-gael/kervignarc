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
//   - « le bouton "Terminer" suit le sportif » — et n'est **jamais bloqué** (`D-15`) ;
//   - « l'administratif à la **gestion** » — donc sur l'écran Paiements réellement monté ;
//   - « le pilotage ne mélange plus » — y compris sur son écran d'**ouverture**, le tableau de bord.
//
// **Ce que la revue a corrigé ici, et qui vaut d'être su.** La première version de ce fichier montait
// les deux composants *isolément* : elle prouvait ce que chacun **rend**, jamais **où** il est
// **monté**. Supprimer `<CompletudeAdministrative>` de `Paiements.tsx` la laissait entièrement verte,
// alors que la moitié « gestion » du CA avait disparu du produit. Un test de placement doit monter
// l'**écran**, pas le composant. Même piège pour le lien de la confirmation : `presentation.test.ts`
// garde la **fonction** `messageConfirmationTerminer`, pas son **site d'appel** — d'où le test qui
// ouvre réellement le dialogue.
//
// Les assertions **négatives** (`queryBy… toBeNull`) restent le cœur du fichier : c'est le mélange
// qui était refusé, donc c'est l'absence qu'il faut prouver. Chacune est **appariée** à une
// assertion positive ailleurs dans le fichier, qui prouve que le libellé nié existe bel et bien
// quelque part — sans quoi une négation reste verte pour la mauvaise raison (libellé renommé,
// composant qui ne rend rien du tout).

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import { Accueil } from '../accueil/Accueil'
import type { Tournoi } from '../competition/api'
import { Paiements } from '../paiements/Paiements'
import type { Completude as CompletudeDTO } from './api'
import { getCompletude } from './api'
import { Completude } from './Completude'
import { CompletudeAdministrative } from './CompletudeAdministrative'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getCompletude: vi.fn(),
}))

// Les écrans réels tirent d'autres sources : on les neutralise pour n'observer que le placement de
// la complétude. Mocker l'`api` (et non les hooks) garde le câblage hook → écran dans le test.
vi.mock('../paiements/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../paiements/api')>()),
  getPaiementsArchers: vi.fn().mockResolvedValue([]),
  getPaiementsClubs: vi.fn().mockResolvedValue([]),
  getRemboursements: vi.fn().mockResolvedValue([]),
}))

vi.mock('../supervision/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../supervision/api')>()),
  getSupervision: vi.fn().mockResolvedValue({ nb_total: 0, nb_en_ligne: 0, postes: [] }),
}))

vi.mock('../accueil/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../accueil/api')>()),
  getTransitions: vi.fn().mockResolvedValue([]),
  getExigenceEffectif: vi.fn().mockResolvedValue({
    origine: 'aucune',
    minimum: null,
    inscrits: 0,
    satisfaite: true,
  }),
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

const TOURNOI: Tournoi = {
  id: 1,
  nom: 'Tournoi de Kervignarc',
  date: '2026-08-07',
  lieu: null,
  type_tournoi: 'officiel',
  statut: 'en_cours',
}

// Le client est créé **hors** du corps du composant : instancié dedans, tout re-rendu du cadre
// jetterait le cache et relancerait les requêtes. Sans effet tant que le cadre est la racine du
// `render`, mais c'est un piège armé pour le premier test qui lui donnerait un état.
function creerClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function Cadre({ enfants, client }: { enfants: ReactNode; client: QueryClient }) {
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

function monter(enfants: ReactNode) {
  return render(<Cadre client={creerClient()} enfants={enfants} />)
}

beforeEach(() => {
  // Sans ce reset, l'historique d'appels s'accumule sur tout le fichier et aucun
  // `toHaveBeenCalledTimes` n'est fiable.
  vi.clearAllMocks()
  vi.mocked(getCompletude).mockResolvedValue(reponse())
})

describe('CA E16US003 — le pilotage ne montre que le sportif', () => {
  it('rend les lignes sportives', async () => {
    monter(<Completude tournoiId={1} statut="en_cours" />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    expect(screen.getByText('Classement')).toBeInTheDocument()
    expect(screen.getByText('28/30 cibles')).toBeInTheDocument()
  })

  it('ne rend AUCUNE ligne administrative — c’est le refus d’A14', async () => {
    const { container } = monter(<Completude tournoiId={1} statut="en_cours" />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    expect(screen.queryByText('Paiements')).toBeNull()
    expect(screen.queryByText('113/120')).toBeNull()
    // Assertion **structurelle** plutôt que sur un titre : elle attrape le retour d'une seconde
    // section quel que soit le nom qu'on lui donnerait. Nier « Hors sportif » ne prouvait rien —
    // ce libellé n'existe plus nulle part, la négation était vraie par vacuité.
    expect(container.querySelectorAll('.completude__section')).toHaveLength(1)
  })

  it('CA — le bouton « Terminer » reste du côté sportif', async () => {
    monter(<Completude tournoiId={1} statut="en_cours" />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Terminer le tournoi' })).toBeInTheDocument()
  })

  it('CA `D-15` — « Terminer » n’est JAMAIS bloqué, même sportif incomplet', async () => {
    // La fixture est volontairement incomplète (`sportif_complet: false`, 28/30 cibles). `D-15` :
    // « l'appli n'empêche pas, elle avertit ». Une garde dure ici interdirait de clore un tournoi
    // pour une cible abandonnée — c'est le scénario que ce test verrouille.
    monter(<Completude tournoiId={1} statut="en_cours" />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Terminer le tournoi' })).toBeEnabled()
  })

  it('CA — la confirmation chiffre les impayés, seul point où les deux mondes se croisent', async () => {
    // Le **contrôle compensatoire** de tout le recentrage : c'est parce que la confirmation annonce
    // encore les impayés que retirer l'administratif de cet écran ne perd rien. Ce test garde le
    // **site d'appel** ; `presentation.test.ts` ne garde que la fonction, donc un « nettoyage » du
    // câblage (passer `hors_sportif: []`, narrower le type) le laisserait vert.
    monter(<Completude tournoiId={1} statut="en_cours" />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: 'Terminer le tournoi' }))

    const dialogue = await screen.findByRole('dialog')
    expect(dialogue).toHaveTextContent('7 archer(s) n’ont pas réglé')
  })
})

describe('CA E16US003 — la gestion porte la complétude administrative', () => {
  it('rend la ligne administrative et son décompte d’archers', async () => {
    monter(<CompletudeAdministrative tournoiId={1} />)

    await waitFor(() => expect(screen.getByText('Paiements')).toBeInTheDocument())
    // Décompte **nu** (pas de suffixe « cibles ») : ce sont des archers réglés, pas des cibles.
    expect(screen.getByText('113/120')).toBeInTheDocument()
    expect(screen.getByText('Complétude administrative')).toBeInTheDocument()
  })

  it('CA — l’écran Paiements (axe gestion) porte réellement cette section', async () => {
    // Le seul test qui garde le **câblage**. Sans lui, supprimer la ligne de `Paiements.tsx` — un
    // « nettoyage » plausible, l'encart n'étant pas le sujet de l'écran — passait tsc, eslint et
    // toute la suite au vert, en supprimant la moitié « gestion » du CA.
    monter(<Paiements tournoiId={1} />)

    await waitFor(() => expect(screen.getByText('Complétude administrative')).toBeInTheDocument())
    expect(screen.getByText('113/120')).toBeInTheDocument()
  })

  it('ne rend AUCUNE ligne sportive, ni le bouton « Terminer »', async () => {
    monter(<CompletudeAdministrative tournoiId={1} />)

    await waitFor(() => expect(screen.getByText('Paiements')).toBeInTheDocument())
    expect(screen.queryByText('Qualification')).toBeNull()
    expect(screen.queryByText('Classement')).toBeNull()
    // Terminer fige le sportif : le proposer depuis un écran de gestion rejouerait le mélange.
    expect(screen.queryByRole('button', { name: 'Terminer le tournoi' })).toBeNull()
  })

  it('CA « une source » — les deux écrans partagent la clé, un seul appel réseau', async () => {
    // Le vrai garde-fou du « sans dupliquer le calcul » : ce n'est pas qu'un appel ait lieu, c'est
    // qu'il n'y en ait **qu'un** pour deux consommateurs. Un second endpoint « complétude
    // administrative », ou une clé React Query divergente, ferait passer ce compte à 2.
    const client = creerClient()
    render(
      <Cadre
        client={client}
        enfants={
          <>
            <Completude tournoiId={7} statut="en_cours" />
            <CompletudeAdministrative tournoiId={7} />
          </>
        }
      />,
    )

    await waitFor(() => expect(screen.getByText('Paiements')).toBeInTheDocument())
    expect(getCompletude).toHaveBeenCalledWith(7)
    expect(getCompletude).toHaveBeenCalledTimes(1)
  })

  it('dit l’erreur sans masquer l’écran des paiements qui l’héberge', async () => {
    vi.mocked(getCompletude).mockRejectedValue(
      new ErreurApi(503, 'indisponible', 'service indisponible'),
    )

    monter(<CompletudeAdministrative tournoiId={1} />)

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent('service indisponible')
  })

  it('ne laisse PAS fuiter le message d’une erreur non-API à l’écran', async () => {
    // Le mode de panne du jour J : LAN coupé → `TypeError: Failed to fetch`, message technique et
    // anglais. Seule une `ErreurApi` porte un texte destiné à l'utilisateur (frontière API).
    vi.mocked(getCompletude).mockRejectedValue(new TypeError('Failed to fetch'))

    monter(<CompletudeAdministrative tournoiId={1} />)

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).not.toHaveTextContent('Failed to fetch')
    expect(screen.getByRole('alert')).toHaveTextContent('Une erreur est survenue.')
  })
})

describe('CA E16US003 — le tableau de bord d’accueil ne mélange plus non plus', () => {
  // `accueil` est la destination d'**ouverture** de l'axe pilotage : y laisser les impayés aurait
  // rejoué le refus d'A14 sur l'écran le plus vu de l'axe — le trou déplacé, pas fermé.
  it('rend le sportif dans « À faire » et n’y met AUCUNE ligne administrative', async () => {
    monter(<Accueil tournoi={TOURNOI} />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    expect(screen.queryByText('Paiements')).toBeNull()
    expect(screen.queryByText('113/120')).toBeNull()
  })

  it('ne construit AUCUNE alerte à partir des impayés', async () => {
    monter(<Accueil tournoi={TOURNOI} />)

    // La ligne « paiements » de la fixture est en état `alerte` : avant E16US003 elle produisait
    // « Paiements : 7 à compléter » dans le bloc Alertes. La qualification, elle, est aussi en
    // `alerte` — son alerte doit rester, sans quoi ce test passerait pour la mauvaise raison.
    await waitFor(() =>
      expect(screen.getByText('Qualification : 2 à compléter')).toBeInTheDocument(),
    )
    expect(screen.queryByText('Paiements : 7 à compléter')).toBeNull()
  })
})
