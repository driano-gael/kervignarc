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

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSessionSuivisStore } from '../../shared/stores/sessionSuivisStore'
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
vi.mock('../tableaux/VueTableaux', () => ({
  VueTableaux: (p: ProprietesTemoin) => rendu('tableaux', p),
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

async function ouvrirLeTournoi() {
  const utilisateur = userEvent.setup()
  render(<AccueilPublic />)
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

    await utilisateur.click(screen.getByRole('button', { name: 'Tableaux' }))
    expect(screen.getByRole('group', { name: 'Affichage' })).toBeInTheDocument()
  })

  it('bascule les cinq vues d’un seul geste, jamais une seule', async () => {
    // C'est tout l'objet de l'US : un interrupteur, pas six. On vérifie la descente sur deux vues
    // servies aussi par l'admin et la salle — celles où une lecture directe du store aurait fui.
    useSessionSuivisStore.setState({ suivis: [{ archerId: 7, tournoiId: 1 }] })

    const utilisateur = await ouvrirLeTournoi()
    await utilisateur.click(screen.getByRole('button', { name: 'Tableaux' }))
    await utilisateur.click(screen.getByRole('button', { name: 'Tout le tournoi' }))

    expect(screen.getByTestId('tableaux')).toHaveTextContent('mode=tout')

    await utilisateur.click(screen.getByRole('button', { name: 'Affectations' }))
    expect(screen.getByTestId('affectations')).toHaveTextContent('mode=tout')
  })

  it('passe les archers suivis en prop à la vue tableaux', async () => {
    // Régression ciblée : `VueTableaux` était la seule des cinq à rebâtir cette liste depuis le
    // store alors qu'elle recevait déjà `mode` en prop — l'exception qui rendait la règle
    // invérifiable, et qui abonnait l'écran de salle à un store public dont il n'a que faire.
    useSessionSuivisStore.setState({
      suivis: [
        { archerId: 7, tournoiId: 1 },
        { archerId: 8, tournoiId: 1 },
      ],
    })

    const utilisateur = await ouvrirLeTournoi()
    await utilisateur.click(screen.getByRole('button', { name: 'Tableaux' }))

    expect(screen.getByTestId('tableaux')).toHaveTextContent('suivis=7,8')
  })
})
