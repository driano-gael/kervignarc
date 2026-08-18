// Tests de **montage** de l'onglet « En cours » (E05US031, ADR-0089).
//
// Ce fichier monte réellement le composant, et c'est délibéré : `VueTableaux.test.tsx` porte le
// récit du défaut qui l'a rendu obligatoire — une boucle de rendu infinie qu'aucune porte mécanique
// (ni `tsc`, ni `eslint`, ni les tests de logique pure) ne pouvait voir. Une feature front sans un
// seul rendu testé a un angle mort de cette taille, et celle-ci est un **aiguilleur** : son défaut
// naturel est précisément d'appeler le mauvais composant, ce que seul un montage attrape.
//
// Les vues de format sont des témoins : ce qu'on garde ici est le **choix** et la **descente des
// props**, pas le rendu de chaque format — chacun a ses propres tests
// (`VuePoulesPublique.test.tsx`, `VueSuissePublique.test.tsx`,
// `VueBigShootOffPublique.test.tsx`).
//
// ⚠️ **Cette dernière phrase était FAUSSE à la première passe de revue, et c'est ce qui a rendu le
// trou acceptable.** Les trois vues n'avaient aucun test ; le fichier affirmait le contraire dans le
// paragraphe même qui raconte pourquoi un rendu non testé est un angle mort. Relevé par trois axes
// (B, C2, adversarial). Une trace qui se lit comme une preuve coûte plus cher qu'une absence de
// trace : c'est la mécanique exacte d'un ADR nommant un module vide (ADR-0075). Les trois fichiers
// existent désormais, et le bloquant de l'US — un compteur d'archers « en lice » qui n'en était pas
// un — a été trouvé par l'un d'eux.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Depart } from '../departs/api'
import { getDeparts } from '../departs/api'
import type { Phase } from '../phases/api'
import { getAvancement } from '../phases/api'
import { VueEnCours } from './VueEnCours'

vi.mock('../departs/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/api')>()),
  getDeparts: vi.fn(),
}))
vi.mock('../phases/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../phases/api')>()),
  getAvancement: vi.fn(),
}))

type Temoin = { phaseId?: number; mode?: string; suivis?: number[] }
const temoin = (nom: string, p: Temoin) => (
  <div
    data-testid={nom}
  >{`${nom} phase=${p.phaseId} mode=${p.mode} suivis=${(p.suivis ?? []).join(',')}`}</div>
)

vi.mock('../poules/VuePoulesPublique', () => ({
  VuePoulesPublique: (p: Temoin) => temoin('poules', p),
}))
vi.mock('../suisse/VueSuissePublique', () => ({
  VueSuissePublique: (p: Temoin) => temoin('suisse', p),
}))
vi.mock('../big-shoot-off/VueBigShootOffPublique', () => ({
  VueBigShootOffPublique: (p: Temoin) => temoin('big-shoot-off', p),
}))
vi.mock('../tableaux/VueTableaux', () => ({
  VueTableaux: (p: Temoin) => temoin('tableaux', p),
}))

const CRENEAU: Depart = {
  id: 41,
  tournoi_id: 1,
  numero: 1,
  horaire: '09:00',
  tarif_centimes: 800,
  quota: null,
  etat: 'ouvert',
}

function phase(patch: Partial<Phase> & Pick<Phase, 'id' | 'ordre' | 'type' | 'statut'>): Phase {
  return {
    depart_id: 41,
    sources: [],
    effectif: 16,
    barrage_jusqu_au: null,
    profondeur: null,
    poules: null,
    big_shoot_off: null,
    suisse: null,
    ...patch,
  }
}

function monter(noeud: ReactNode) {
  // `retry: false` : un test ne doit pas attendre les reprises de React Query.
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{noeud}</QueryClientProvider>)
}

beforeEach(() => {
  vi.mocked(getDeparts).mockResolvedValue([CRENEAU])
  vi.mocked(getAvancement).mockReset()
})

describe('VueEnCours — l’aiguillage par format', () => {
  it('rend les poules quand la phase en cours est une phase de poules', async () => {
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 7, ordre: 1, type: 'qualification', statut: 'terminee' }),
      phase({ id: 8, ordre: 2, type: 'poules', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)

    expect(await screen.findByTestId('poules')).toHaveTextContent('phase=8')
    expect(screen.queryByTestId('suisse')).toBeNull()
  })

  it('rend le système suisse, et lui impose la phase choisie', async () => {
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 9, ordre: 1, type: 'suisse', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)

    expect(await screen.findByTestId('suisse')).toHaveTextContent('phase=9')
  })

  it('rend le Big Shoot Off', async () => {
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 10, ordre: 1, type: 'big_shoot_off', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)

    expect(await screen.findByTestId('big-shoot-off')).toHaveTextContent('phase=10')
  })

  it('impose la phase à la vue des tableaux, au lieu de la laisser choisir la sienne', async () => {
    // ⚠️ **Le cas qui justifie la prop `phaseId` ajoutée à `VueTableaux`.** Un départ porte
    // couramment deux tableaux (principal + consolante) ; sans cette prop, le fil du déroulé
    // annoncerait « 3. Placement » au-dessus de l'arbre du tableau principal.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 11, ordre: 1, type: 'elimination_directe', statut: 'terminee' }),
      phase({ id: 12, ordre: 2, type: 'placement', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)

    expect(await screen.findByTestId('tableaux')).toHaveTextContent('phase=12')
  })

  it('renvoie vers le classement pour une qualification, sans afficher de liste vide', async () => {
    // Un tir au cumul n'a pas de rencontre à suivre : son résultat *est* le classement. Rendre une
    // liste vide ferait croire à un plan de salle non posé.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 13, ordre: 1, type: 'qualification', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)

    expect(await screen.findByText(/Le résultat se lit sur/)).toBeInTheDocument()
  })

  it('nomme un format qu’il ne sait pas encore dessiner au lieu de rendre une page blanche', async () => {
    // La colline (E05US027 reste à livrer). Un écran de salle n'a personne devant lui pour
    // comprendre ce qui manque : le silence y est indétectable.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 14, ordre: 1, type: 'colline', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)

    expect(await screen.findByText(/ne s’affiche pas encore ici/)).toBeInTheDocument()
  })
})

describe('VueEnCours — le fil du déroulé', () => {
  it('atterrit sur la phase en cours et laisse remonter aux précédentes', async () => {
    // Le CA du 18/08/2026 : « l'écran se place sur la phase en cours », **avec** remontée de
    // l'historique. Les deux moitiés sont ici — on arrive sur les poules, on revient au tableau.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 20, ordre: 1, type: 'elimination_directe', statut: 'terminee' }),
      phase({ id: 21, ordre: 2, type: 'poules', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)
    expect(await screen.findByTestId('poules')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /1\. Élimination directe/ }))

    await waitFor(() => expect(screen.getByTestId('tableaux')).toHaveTextContent('phase=20'))
    expect(screen.queryByTestId('poules')).toBeNull()
  })

  it('n’offre aucun fil sur l’écran projeté, où personne ne peut cliquer', async () => {
    // CA E07US004 : aucune interaction. Un fil de déroulé figé sur une phase close pendant qu'on
    // tire la suivante serait le pire des deux mondes.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 22, ordre: 1, type: 'elimination_directe', statut: 'terminee' }),
      phase({ id: 23, ordre: 2, type: 'poules', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} interactif={false} />)

    expect(await screen.findByTestId('poules')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Déroulé du départ' })).toBeNull()
  })

  it('descend le mode et les archers suivis au format aiguillé', async () => {
    // L'interrupteur d'ADR-0079 est **unique pour tout l'onglet public** : il vaut donc aussi de
    // l'autre côté de l'aiguillage, sans quoi le spectateur le verrait sans effet sur une poule.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 24, ordre: 1, type: 'poules', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="suivis" suivis={[7, 8]} />)

    expect(await screen.findByTestId('poules')).toHaveTextContent('mode=suivis suivis=7,8')
  })

  it('dit que le déroulé n’est pas composé plutôt que de rester vide', async () => {
    vi.mocked(getAvancement).mockResolvedValue([])

    monter(<VueEnCours tournoiId={1} />)

    expect(await screen.findByText(/n’est pas encore composé/)).toBeInTheDocument()
  })
})
