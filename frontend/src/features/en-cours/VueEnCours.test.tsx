// Tests de **montage** de l'onglet « En cours » (E05US031, ADR-0089).
//
// Ce fichier monte réellement le composant : `VueTableaux.test.tsx` porte le récit du défaut qui
// l'a rendu obligatoire, et cette feature est un **aiguilleur** — son défaut naturel est d'appeler
// le mauvais composant, ce que seul un montage attrape. ⚠️ La phrase « chaque format a ses propres
// tests » était **fausse** à la première passe, dans le paragraphe même qui explique pourquoi un
// rendu non testé est un angle mort : une trace qui se lit comme une preuve coûte plus cher qu'une
// absence de trace. Les trois fichiers existent désormais.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Depart } from '../departs/api'
import { getDeparts } from '../departs/api'
import type { TypePhase } from '../../shared/phases/catalogue'
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
vi.mock('../colline/VueCollinePublique', () => ({
  VueCollinePublique: (p: Temoin) => temoin('colline', p),
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
    colline: null,
    decoupage: null,
    // ⚠️ E05US033 : `arrets` n'est **pas** ici, et c'est voulu — une `Phase` ne les porte pas, le
    // serveur ne les remplit que sur une étape de déroulé (le type l'exclut explicitement).
    // ⚠️ E05US035 : `nb_volees` non plus, et pour la même raison — il n'est servi que sur une
    // étape, le barème se lisant par sa propre ressource.
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

  it('nomme un format que cette version ne sait pas dessiner au lieu de rendre une page blanche', async () => {
    // ⚠️ **Ce test a changé de cible en E05US027** : il visait la colline, seul format sans vue ;
    // celle-ci livrée, **plus aucun `TypePhase` connu du bundle** ne tombe dans le repli — le
    // `switch` est exhaustif et le compilateur l'impose. Le cas couvert reste pourtant réel, et
    // c'est le seul que le compilateur ne peut pas voir : un **serveur plus récent** que ce bundle.
    // Le `as` est ici la **seule** façon d'exercer la branche, pas un contournement de typage — et
    // un écran de salle n'a personne devant lui pour comprendre ce qui manque.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({
        id: 14,
        ordre: 1,
        type: 'format_du_futur' as unknown as TypePhase,
        statut: 'en_cours',
      }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)

    expect(await screen.findByText(/n’a pas de rendu dans cette version/)).toBeInTheDocument()
  })

  it('aiguille vers la vue de la colline, jouable depuis E05US027', async () => {
    // La contrepartie du test ci-dessus : le format que le repli citait a désormais sa vue. Sans ce
    // cas, retirer la branche du `switch` ferait retomber la colline dans le repli sans que rien ne
    // rougisse — le bandeau « pas de rendu dans cette version » est plausible, et faux.
    //
    // Comme ses trois voisins, ce test éprouve l'**aiguillage** et non le rendu : la vue est mockée
    // ici, et son contenu est éprouvé dans `VueCollinePublique.test.tsx`.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 14, ordre: 1, type: 'colline', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)

    await waitFor(() => expect(screen.getByTestId('colline')).toHaveTextContent('phase=14'))
  })
})

describe('VueEnCours — l’annonce de pause (CA E05US034)', () => {
  // Le CA : « un spectateur qui voit la salle immobile et un écran qui n'annonce rien conclut à une
  // panne ». La règle est un rendu conditionnel, donc invisible à tout test qui ne monte pas le
  // composant — le trou relevé sur ce fichier même en revue d'E05US031, et re-relevé ici (axe B).

  it('annonce la pause quand la phase en cours est arrêtée', async () => {
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 12, ordre: 1, type: 'suisse', statut: 'en_pause' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)

    expect(await screen.findByText(/le tir est suspendu par l’organisation/i)).toBeInTheDocument()
  })

  it('laisse l’écran projeté annoncer la pause lui-même, sans doubler le bandeau', async () => {
    // ⚠️ Correctif de 2ᵉ passe : l'écran de salle porte un bandeau **permanent**, hors de sa
    // rotation de vues. Si son déroulé contient « En cours », les deux bandeaux s'empilaient — sur
    // un projecteur, en 1,1 em. `interactif={false}` est la marque de cette surface : elle a déjà
    // son annonce.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 12, ordre: 1, type: 'suisse', statut: 'en_pause' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} interactif={false} />)

    expect(await screen.findByTestId('suisse')).toBeInTheDocument()
    expect(screen.queryByText(/le tir est suspendu par l’organisation/i)).toBeNull()
  })

  it('n’annonce rien quand la salle tire', async () => {
    // ⚠️ Le cas adverse porte l'essentiel : sans lui, un bandeau rendu **inconditionnellement**
    // passerait au vert et annoncerait une pause sur une salle qui tire — pire que pas d'annonce.
    vi.mocked(getAvancement).mockResolvedValue([
      phase({ id: 12, ordre: 1, type: 'suisse', statut: 'en_cours' }),
    ])

    monter(<VueEnCours tournoiId={1} mode="tout" suivis={[]} />)

    expect(await screen.findByTestId('suisse')).toBeInTheDocument()
    expect(screen.queryByText(/le tir est suspendu par l’organisation/i)).toBeNull()
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
