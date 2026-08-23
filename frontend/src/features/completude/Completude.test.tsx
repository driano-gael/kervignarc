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
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import { Accueil } from '../accueil/Accueil'
import type { ExigenceEffectif } from '../accueil/api'
import { getExigenceEffectif, getTransitions } from '../accueil/api'
import type { Tournoi } from '../competition/api'
import type { LignePaiementArcher } from '../paiements/api'
import {
  getPaiementsArchers,
  getPaiementsClubs,
  getRemboursements,
  marquerArcher,
} from '../paiements/api'
import { Paiements } from '../paiements/Paiements'
import type { Supervision } from '../supervision/api'
import { getSupervision } from '../supervision/api'
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
//
// ⚠️ Les fixtures sont **typées** (`satisfait: ExigenceEffectif`, etc.). Les `vi.fn()` d'une factory
// `vi.mock` ne le sont pas : sans annotation explicite, une fixture qui s'éloigne de son DTO passe
// `tsc` sans bruit, et le test finit par passer *pour la mauvaise raison* — un champ manquant lu
// comme `undefined` prend silencieusement la branche « tout va bien ».
vi.mock('../paiements/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../paiements/api')>()),
  getPaiementsArchers: vi.fn(),
  getPaiementsClubs: vi.fn(),
  getRemboursements: vi.fn(),
  marquerArcher: vi.fn(),
}))

vi.mock('../supervision/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../supervision/api')>()),
  getSupervision: vi.fn(),
}))

vi.mock('../accueil/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../accueil/api')>()),
  getTransitions: vi.fn(),
  getExigenceEffectif: vi.fn(),
}))

const SUPERVISION: Supervision = {
  postes: [],
  nb_en_ligne: 0,
  nb_total: 0,
  nb_ecrans_en_ligne: 0,
  nb_ecrans: 0,
}

const EXIGENCE: ExigenceEffectif = {
  inscrits: 0,
  minimum: 0,
  suffisant: true,
  origine: 'aucune',
  ordre_phase: null,
  rang_debut: null,
}

// Registre de paiements **réaliste** : 120 inscrits dont 113 réglés, cohérent avec la ligne
// `paiements 113/120` de la complétude. Une fixture vide rendrait « 0/0 » à l'entête de l'accueil et
// ferait passer pour la mauvaise raison l'assertion qui distingue le **repère** de la **tâche**.
function registrePaiements(regles = 113, total = 120): LignePaiementArcher[] {
  return Array.from({ length: total }, (_, i) => ({
    archer_id: i + 1,
    nom: `Nom${i}`,
    prenom: `Prenom${i}`,
    club_id: null,
    recap: {
      du_centimes: 1000,
      paye_centimes: i < regles ? 1000 : 0,
      reste_centimes: i < regles ? 0 : 1000,
    },
  }))
}

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
  // `clearAllMocks` = `mockClear` : il vide l'**historique d'appels**, pas les implémentations. Sans
  // lui, l'historique s'accumule sur tout le fichier et aucun `toHaveBeenCalledTimes` n'est fiable.
  vi.clearAllMocks()
  vi.mocked(getCompletude).mockResolvedValue(reponse())
  vi.mocked(getPaiementsArchers).mockResolvedValue(registrePaiements())
  vi.mocked(getPaiementsClubs).mockResolvedValue([])
  vi.mocked(getRemboursements).mockResolvedValue([])
  vi.mocked(getSupervision).mockResolvedValue(SUPERVISION)
  vi.mocked(getTransitions).mockResolvedValue([])
  vi.mocked(getExigenceEffectif).mockResolvedValue(EXIGENCE)
})

describe('CA E16US003 — le pilotage ne montre que le sportif', () => {
  it('rend les lignes sportives, sous le titre « Prêt à terminer ? »', async () => {
    monter(<Completude tournoiId={1} statut="en_cours" />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    expect(screen.getByText('Classement')).toBeInTheDocument()
    expect(screen.getByText('28/30 cibles')).toBeInTheDocument()
    // Le renommage est un **arbitrage du commanditaire** (« Complétude du déroulé » entrait en
    // collision avec « Suivi du déroulé »). Sans cette ligne il repartait sans filet mécanique :
    // remettre l'ancien titre laissait toute la suite verte.
    expect(screen.getByRole('heading', { name: 'Prêt à terminer ?' })).toBeInTheDocument()
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

  it('E16US012 `D-15` — le verdict avertit sans annoncer de refus', async () => {
    // L'écran a migré sur la coquille commune de la famille « prêt à… » (ADR-0096), qui lui ajoute
    // un verdict en tête. Ce verdict doit rester du **bon côté de l'asymétrie** : terminer n'a
    // aucune garde dure, donc l'écran ne doit jamais annoncer un refus qui n'arrivera pas.
    //
    // C'est la contrepartie du `bloquant` passé par cet écran : si quelqu'un le mettait à `true`
    // « par symétrie » avec l'écran de démarrage, ce test tomberait — et c'est le seul endroit où
    // cette erreur-là se verrait, le typage ne disant rien d'un booléen inversé.
    //
    // ⚠️ **Pendant le tournoi**, et c'est le sujet des deux tests suivants.
    monter(<Completude tournoiId={1} statut="en_cours" />)

    const verdict = await screen.findByRole('status')
    expect(verdict).toHaveTextContent('ne vous en empêchera pas')
    expect(verdict).not.toHaveTextContent('refusé')
  })

  it('E16US012 — hors du tournoi en cours, le verdict n’affirme pas que rien n’empêche', async () => {
    // **Le bloquant de la 2ᵉ passe de revue.** `ServiceTournois.terminer` n'accepte que `en_cours`
    // (`{StatutTournoi.EN_COURS}`) : sur un tournoi **en pause** — la pause déjeuner du jour J —
    // terminer est refusé tant qu'on n'a pas repris. Avec `bloquant={false}` figé, l'écran
    // affichait « l'application ne vous en empêchera pas » juste avant un 409, c'est-à-dire la
    // phrase même que cette US déclarait avoir supprimée, sur le membre voisin de la famille.
    //
    // Ce test est le miroir de `domain.jalon.evaluer_terminer` : il tombe si l'un des deux bouge
    // sans l'autre. C'est le prix assumé de laisser cet écran lire `/completude` plutôt que
    // `/jalons/terminer` (ADR-0096 § Conséquences : un second poll de 5 s par tablette).
    monter(<Completude tournoiId={1} statut="en_pause" />)

    const verdict = await screen.findByRole('status')
    expect(verdict).toHaveTextContent('sera refusé')
    expect(verdict).not.toHaveTextContent('ne vous en empêchera pas')
    expect(screen.getByText(/Seul un tournoi en cours peut être terminé/)).toBeInTheDocument()
  })

  it('E16US012 — un tournoi terminé ne s’entend pas dire que rien ne s’y oppose', async () => {
    // L'autre moitié du même défaut : avec le sportif complet, `pret` valait `true` quel que soit
    // le statut, donc « Oui — rien ne s'y oppose » s'affichait deux lignes au-dessus de « Ce
    // tournoi est terminé : le sportif est figé. » — la contradiction que l'écran de démarrage
    // venait précisément de fermer.
    const complet = reponse()
    vi.mocked(getCompletude).mockResolvedValue({
      ...complet,
      sportif: complet.sportif.map((ligne) => ({ ...ligne, etat: 'ok' as const })),
      sportif_complet: true,
    })
    monter(<Completude tournoiId={1} statut="termine" />)

    expect(await screen.findByRole('status')).not.toHaveTextContent('rien ne s’y oppose')
  })

  it('CA `D-15` — même complétude injoignable, le bouton reste : on dégrade, on ne verrouille pas', async () => {
    // L'autre moitié de `D-15`, et celle qui manquait : le bouton vivait **dans** la garde
    // `completude.data`, donc une lecture en échec le faisait disparaître — l'appli empêchait au lieu
    // d'avertir. `P-3` : ne jamais bloquer la seule action irréversible sur un hoquet réseau.
    vi.mocked(getCompletude).mockRejectedValue(new TypeError('Failed to fetch'))

    monter(<Completude tournoiId={1} statut="en_cours" />)

    const bouton = await screen.findByRole('button', { name: 'Terminer le tournoi' })
    expect(bouton).toBeEnabled()

    await userEvent.click(bouton)
    expect(await screen.findByRole('dialog')).toHaveTextContent(
      'Impossible de vérifier ce qui reste',
    )
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

  it('CA « une source » — marquer un règlement rafraîchit AUSSI le décompte du haut', async () => {
    // La seule vraie modification de comportement du recentrage, et elle n'était gardée par rien :
    // sans l'invalidation de `['completude']`, la ligne du tableau bascule sur « Réglé » pendant que
    // l'encart garde l'ancien compte jusqu'au tick de poll (5 s). Le même écran se contredit —
    // exactement ce que « deux écrans, une source » veut rendre impossible.
    vi.mocked(marquerArcher).mockResolvedValue(registrePaiements()[119]!)
    monter(<Paiements tournoiId={1} />)

    await waitFor(() => expect(screen.getByText('Complétude administrative')).toBeInTheDocument())
    expect(getCompletude).toHaveBeenCalledTimes(1)

    await userEvent.click(screen.getAllByRole('button', { name: /Marquer réglé/ })[0]!)

    await waitFor(() => expect(getCompletude).toHaveBeenCalledTimes(2))
  })
})

describe('CA E16US003 — le tableau de bord d’accueil ne mélange plus non plus', () => {
  // `accueil` est la destination d'**ouverture** de l'axe pilotage : y laisser les impayés aurait
  // rejoué le refus d'A14 sur l'écran le plus vu de l'axe — le trou déplacé, pas fermé.
  it('rend le sportif dans « À faire » et n’y met AUCUNE ligne administrative', async () => {
    const { container } = monter(<Accueil tournoi={TOURNOI} />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    // Négation **bornée à la checklist**, pas à l'écran : « 113/120 » doit au contraire s'afficher
    // dans l'entête (cf. le test suivant). Nier son absence de tout l'écran encodait l'inverse du
    // CA, et ne passait que parce que la fixture de paiements était vide.
    const checklist = container.querySelector('.checklist')!
    expect(within(checklist as HTMLElement).queryByText('Paiements')).toBeNull()
    expect(within(checklist as HTMLElement).queryByText('113/120')).toBeNull()
  })

  it('CA — le repère « Réglés » de l’entête RESTE : un repère n’est pas une tâche', async () => {
    // C'est le critère de partage retenu à l'arbitrage, et il n'était gardé par rien : supprimer le
    // chiffre-clé laissait toute la suite verte. Savoir où l'on en est ≠ se voir réclamer une tâche.
    const { container } = monter(<Accueil tournoi={TOURNOI} />)

    await waitFor(() => expect(screen.getByText('Qualification')).toBeInTheDocument())
    const chiffres = container.querySelector('.accueil__chiffres')!
    expect(within(chiffres as HTMLElement).getByText('Réglés')).toBeInTheDocument()
    expect(within(chiffres as HTMLElement).getByText('113/120')).toBeInTheDocument()
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
