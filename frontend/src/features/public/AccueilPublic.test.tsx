// Tests de **montage** de la coquille publique (E07US001, interrupteur global d'E16US004).
//
// Ce fichier couvre ce qui ne vit nulle part ailleurs : la **composition** de l'onglet public. Les
// six vues sont mockées à dessein — chacune a ses propres tests, et les monter pour de vrai ferait
// de ce fichier un test d'intégration lent qui échouerait pour des raisons étrangères à son sujet.
// Ce qu'on vérifie ici, c'est l'assemblage : quel mode descend, à qui, et quand l'interrupteur
// s'affiche.
//
// Trois raisons de son existence, toutes issues de la revue d'E16US004 :
//
//  1. **C'est ici que se décide le défaut d'ouverture.** Le CA d'E07US005 promet « *Mon chemin* par
//     défaut dès qu'on suit quelqu'un » ; depuis qu'un interrupteur unique gouverne les cinq vues,
//     ce défaut n'est plus porté par `VueTableaux` mais par la valeur initiale du store. Le test
//     qui le gardait a disparu avec le sélecteur local — le voici, à la bonne adresse.
//  2. **C'est le lecteur du store qui dessert les cinq vues partagées.** Le piège du sélecteur
//     Zustand instable (`getSnapshot` qui rend un tableau neuf → boucle de rendu infinie en Zustand
//     v5 / React 19) n'a pas été corrigé, il a **changé d'adresse** : `VueTableaux` reçoit désormais
//     ses suivis en prop. Monter ce composant est ce qui détecte la rechute ici.
//     ⚠️ **Ce n'est pas le seul lecteur restant** (rectification de la 2ᵉ passe, qui a repris une
//     affirmation fausse) : `VueSuivi` lit le store lui aussi, pour composer la liste — et ce
//     fichier le **mocke**, donc ne le couvre pas. `VueSuivi` n'a à ce jour aucun test de montage,
//     alors que c'est le composant qui a le plus changé dans cette US ; c'est un angle mort connu,
//     inscrit comme tel plutôt que masqué par un commentaire optimiste.
//  3. **L'interrupteur ne doit pas s'afficher là où il n'agit pas** — l'onglet « Suivi », qui est
//     précisément celui d'atterrissage.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSessionSuivisStore } from '../../shared/stores/sessionSuivisStore'
import type { Identite } from '../identite/api'
import { getIdentite } from '../identite/api'
import { AccueilPublic } from './AccueilPublic'

// ⚠️ Les factories de `vi.mock` sont **hoistées** en tête de fichier : elles ne peuvent référencer
// aucune variable de module (d'où les définitions inline plutôt qu'un helper partagé).
//
// La liste de tournois n'est pas le sujet : on la remplace par un bouton qui sélectionne d'emblée.
vi.mock('../tournois/Tournois', () => ({
  GestionTournois: ({ onChoisi }: { onChoisi: (t: unknown) => void }) => (
    <button
      type="button"
      onClick={() =>
        onChoisi({
          id: 1,
          nom: 'Kervignarc 2026',
          date: '2026-02-14',
          lieu: 'Gymnase',
          type_tournoi: 'salle_18m',
          statut: 'en_cours',
        })
      }
    >
      Choisir le tournoi
    </button>
  ),
}))

// Chaque vue est réduite à un témoin qui **réémet ses props** : c'est le contrat de descente qu'on
// teste, pas le rendu des vues.
type ProprietesTemoin = { mode?: string; suivis?: number[] }
const rendu = (nom: string, { mode, suivis }: ProprietesTemoin) => (
  <div
    data-testid={nom}
  >{`${nom} mode=${mode ?? 'absent'} suivis=${(suivis ?? []).join(',')}`}</div>
)

vi.mock('../suivi/VueSuivi', () => ({
  VueSuivi: () => <div data-testid="suivi">suivi</div>,
}))
vi.mock('../competition/VueClassement', () => ({
  VueClassement: (p: ProprietesTemoin) => rendu('classement', p),
}))
vi.mock('../en-cours/VueEnCours', () => ({
  VueEnCours: (p: ProprietesTemoin) => rendu('en-cours', p),
}))
vi.mock('../routage/VueAffectations', () => ({
  VueAffectations: (p: ProprietesTemoin) => rendu('affectations', p),
}))
vi.mock('../palmares/VuePalmares', () => ({
  VuePalmares: (p: ProprietesTemoin) => rendu('palmares', p),
}))
vi.mock('../placement/PlanCiblesPublic', () => ({
  PlanCiblesPublic: (p: ProprietesTemoin) => rendu('plan', p),
}))
vi.mock('../competition/BadgeStatut', () => ({ BadgeStatut: () => null }))
// E16US006 : l'identité est servie par une doublure typée plutôt que par la neutralisation de
// `HabillageIdentite` — c'est **son montage** que le dernier bloc vérifie.
vi.mock('../identite/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../identite/api')>()),
  getIdentite: vi.fn(),
}))

/**
 * ⚠️ **Le `QueryClientProvider` est arrivé avec E16US006**, et son absence était un faux confort.
 *
 * Jusqu'ici ce fichier montait `AccueilPublic` sans client : toutes les vues étaient réduites à des
 * témoins, donc plus rien n'interrogeait le serveur. L'habillage d'identité, lui, est un vrai
 * consommateur de React Query — comme l'application réelle, qui pose ce provider dans
 * `app/providers.tsx`. Le harnais rejoint donc la réalité au lieu de s'en écarter.
 */
function monter(noeud: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{noeud}</QueryClientProvider>)
}

async function ouvrirLeTournoi() {
  const utilisateur = userEvent.setup()
  monter(<AccueilPublic />)
  await utilisateur.click(screen.getByRole('button', { name: 'Choisir le tournoi' }))
  return utilisateur
}

describe('AccueilPublic — interrupteur « mes archers / tout »', () => {
  beforeEach(() => {
    // ⚠️ **`getInitialState()`, jamais une valeur écrite à la main** (2ᵉ passe de revue). Un premier
    // jet posait `centrerSurSuivis: true` ici — le test « ouvre centré » **armait donc lui-même** ce
    // qu'il prétendait observer, et serait resté vert avec le défaut inverse. Repartir de l'état
    // initial du store fait que ce fichier exerce le **vrai** défaut d'ouverture, celui du CA
    // d'E07US005 ; le changer ferait échouer ce test, ce qui est tout l'intérêt.
    useSessionSuivisStore.setState(useSessionSuivisStore.getInitialState())
  })

  it('ouvre centré sur ses archers quand on en suit (CA E07US005, D-09)', async () => {
    // ⚠️ **L'arbitrage du 08/08/2026.** Sans cette valeur initiale armée, l'US révoquait en silence
    // un CA déjà livré : le spectateur qui suit trois archers atterrissait sur l'arbre complet et
    // sur le classement entier, alors qu'E07US005 promet l'inverse. Le CA est honoré ici.
    useSessionSuivisStore.setState({ suivis: [{ archerId: 7, tournoiId: 1 }] })

    const utilisateur = await ouvrirLeTournoi()
    await utilisateur.click(screen.getByRole('button', { name: 'Classement' }))

    expect(screen.getByTestId('classement')).toHaveTextContent('mode=suivis')
    expect(screen.getByTestId('classement')).toHaveTextContent('suivis=7')
  })

  it('retombe sur « tout le tournoi » quand on ne suit personne ici', async () => {
    // `modeEffectif` : la préférence est **globale**, les suivis sont **par tournoi**. Sans ce
    // garde, ouvrir un tournoi où l'on ne suit personne viderait les cinq écrans sans rien dire.
    useSessionSuivisStore.setState({ suivis: [{ archerId: 7, tournoiId: 99 }] })

    await ouvrirLeTournoi()

    expect(screen.getByTestId('classement')).toHaveTextContent('mode=tout')
    // Et l'interrupteur n'est pas proposé : il n'aurait rien à centrer.
    expect(screen.queryByRole('group', { name: 'Affichage' })).toBeNull()
  })

  it('n’affiche pas l’interrupteur sur l’onglet « Suivi », qui ne le lit pas', async () => {
    // L'onglet d'atterrissage dès qu'on suit quelqu'un : y proposer un réglage sans effet visible
    // faisait douter du reste de l'écran.
    useSessionSuivisStore.setState({ suivis: [{ archerId: 7, tournoiId: 1 }] })

    const utilisateur = await ouvrirLeTournoi()

    expect(screen.getByTestId('suivi')).toBeInTheDocument()
    expect(screen.queryByRole('group', { name: 'Affichage' })).toBeNull()

    await utilisateur.click(screen.getByRole('button', { name: 'En cours' }))
    expect(screen.getByRole('group', { name: 'Affichage' })).toBeInTheDocument()
  })

  it('bascule les cinq vues d’un seul geste, jamais une seule', async () => {
    // C'est tout l'objet de l'US : un interrupteur, pas six. On vérifie la descente sur deux vues
    // servies aussi par l'admin et la salle — celles où une lecture directe du store aurait fui.
    useSessionSuivisStore.setState({ suivis: [{ archerId: 7, tournoiId: 1 }] })

    const utilisateur = await ouvrirLeTournoi()
    await utilisateur.click(screen.getByRole('button', { name: 'En cours' }))
    await utilisateur.click(screen.getByRole('button', { name: 'Tout le tournoi' }))

    expect(screen.getByTestId('en-cours')).toHaveTextContent('mode=tout')

    await utilisateur.click(screen.getByRole('button', { name: 'Affectations' }))
    expect(screen.getByTestId('affectations')).toHaveTextContent('mode=tout')
  })

  it('passe les archers suivis en prop à la vue « En cours »', async () => {
    // Régression ciblée : `VueTableaux` était la seule des cinq à rebâtir cette liste depuis le
    // store alors qu'elle recevait déjà `mode` en prop — l'exception qui rendait la règle
    // invérifiable, et qui abonnait l'écran de salle à un store public dont il n'a que faire.
    //
    // ⚠️ La vue en question est `VueEnCours` depuis E05US031 : elle a pris la place de l'onglet
    // « Tableaux » et **descend** ces deux props à chaque format qu'elle aiguille. La règle porte
    // donc désormais sur une chaîne de deux composants, et c'est le premier maillon qu'on garde
    // ici — le second est couvert par `VueEnCours.test.tsx`.
    useSessionSuivisStore.setState({
      suivis: [
        { archerId: 7, tournoiId: 1 },
        { archerId: 8, tournoiId: 1 },
      ],
    })

    const utilisateur = await ouvrirLeTournoi()
    await utilisateur.click(screen.getByRole('button', { name: 'En cours' }))

    expect(screen.getByTestId('en-cours')).toHaveTextContent('suivis=7,8')
  })
})

describe('AccueilPublic — l’identité du tournoi habille l’appli publique (CA E16US006, D-27)', () => {
  // ⚠️ **Test de PLACEMENT** (cf. `DETTE-085`) : monter `HabillageIdentite` seul prouverait qu'il
  // sait poser des jetons, pas que l'appli publique l'appelle. Ce bloc tombe si on retire
  // l'habillage ou le logo des vues d'un tournoi.

  beforeEach(() => {
    useSessionSuivisStore.setState(useSessionSuivisStore.getInitialState())
    vi.mocked(getIdentite).mockResolvedValue(identitePublique())
  })

  it('pose les jetons du tournoi une fois un tournoi choisi', async () => {
    const { container } = monter(<AccueilPublic />)
    await userEvent.click(screen.getByRole('button', { name: 'Choisir le tournoi' }))

    await waitFor(() =>
      expect(container.querySelector('style')?.textContent).toContain('--brand-surface:#0b6e9e'),
    )
    expect(container.querySelector('[data-identite="identite-1"]')).not.toBeNull()
  })

  it('n’habille PAS la liste des tournois', async () => {
    // ⚠️ La liste n'appartient à aucune édition : l'habiller aux couleurs de la première la ferait
    // mentir. Assertion négative **appariée** à la positive ci-dessus, qui prouve que l'habillage
    // existe bel et bien une fois un tournoi ouvert.
    const { container } = monter(<AccueilPublic />)

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Choisir le tournoi' })).toBeInTheDocument(),
    )
    expect(container.querySelector('[data-identite]')).toBeNull()
  })

  it('affiche le logo du tournoi à côté de son nom', async () => {
    vi.mocked(getIdentite).mockResolvedValue({ ...identitePublique(), logos: ['evenement'] })

    monter(<AccueilPublic />)
    await userEvent.click(screen.getByRole('button', { name: 'Choisir le tournoi' }))

    expect(await screen.findByAltText(/Logo du tournoi/i)).toBeInTheDocument()
  })
})

/** Une identité réglée en bleu, distincte du rouge du club : avec les couleurs héritées, un
 *  habillage absent rendrait exactement le même écran et l'assertion ne prouverait rien. */
function identitePublique(): Identite {
  const jetons = { surface: '#0b6e9e', contour: '#0b6e9e', texte: '#3aa8dd', encre: '#ffffff' }
  const accent = {
    couleur: '#0b6e9e',
    sombre: jetons,
    clair: jetons,
    contraste_sur_sombre: 4.6,
    contraste_sur_clair: 4.6,
  }
  return {
    reglee: true,
    primaire: accent,
    secondaire: accent,
    logos: [],
    seuil_contour: 3,
    seuil_texte: 4.5,
  }
}
