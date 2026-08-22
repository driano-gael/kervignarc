// Tests de **montage** de la vue publique de la colline (E05US027, ADR-0089).
//
// Écrits d'emblée plutôt qu'en correctif : la revue d'E05US031 a dû les ajouter après coup au
// suisse, et deux défauts réels y avaient échappé — le porteur du bye passait à travers le filtre
// « mes archers », et les conflits de pose n'étaient pas annoncés alors que la vue des poules le
// fait sur le même champ. Les deux ont leur pendant ici : les archers **au repos** et l'annonce des
// cibles manquantes.
//
// ⚠️ **Ce que cette vue a de particulier, et qui justifie ses propres cas** : la colline ne montre
// pas des rencontres mais des **positions qui bougent**. Un rendu qui perdrait « le 6 défie le 4 »
// resterait parfaitement lisible — et vide de ce que le format apporte.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { DefiPublic, EtatCollinePublique, ManchePublique } from './api'
import { getEtatColline } from './api'
import { VueCollinePublique } from './VueCollinePublique'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getEtatColline: vi.fn(),
}))

const MARTIN = { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' }
const DURAND = { archer_id: 2, nom: 'DURAND', prenom: 'Aline' }
const PETIT = { archer_id: 3, nom: 'PETIT', prenom: 'Jo' }

function defi(patch: Partial<DefiPublic> & Pick<DefiPublic, 'numero' | 'manche'>): DefiPublic {
  return {
    position_haute: 1,
    position_basse: 2,
    couloirs: null,
    haut: MARTIN,
    bas: DURAND,
    points_haut: null,
    points_bas: null,
    vainqueur: null,
    termine: false,
    validee: false,
    desynchronisee: false,
    ...patch,
  }
}

function manche(patch: Partial<ManchePublique> & Pick<ManchePublique, 'numero'>): ManchePublique {
  return {
    defis: [defi({ numero: patch.numero, manche: patch.numero })],
    au_repos: [],
    close: false,
    ...patch,
  }
}

function etat(patch: Partial<EtatCollinePublique> = {}): EtatCollinePublique {
  return {
    phase_id: 9,
    nb_manches: 3,
    portee_de_defi: 1,
    portee_maximale: 2,
    effectif: 3,
    manches: [manche({ numero: 1, close: true }), manche({ numero: 2 })],
    classement: [
      { position: 1, archer_id: 1 },
      { position: 2, archer_id: 2 },
    ],
    conflits: [],
    ...patch,
  }
}

function monter(noeud: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{noeud}</QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getEtatColline).mockResolvedValue(etat())
})

describe('la vue publique de la colline', () => {
  it('atterrit sur la manche qui se joue, pas sur la première', () => {
    // Une colline ré-apparie à chaque manche : les afficher toutes noierait celle que la salle
    // regarde. Même règle que le suisse et que `VueTableaux`.
    monter(<VueCollinePublique tournoiId={1} phaseId={9} />)

    return screen.findByText(/Manche 2 sur 3/).then((noeud) => {
      expect(noeud).toBeInTheDocument()
    })
  })

  it('nomme le format d’après la portée, pas seulement le nombre', async () => {
    // Le catalogue n'expose qu'un type « colline » (règle 2), mais le spectateur entend son club
    // dire « King of the Hill » ou « Ladder ». Un « portée 1 » nu ne lui apprend rien.
    monter(<VueCollinePublique tournoiId={1} phaseId={9} />)

    expect(await screen.findByText(/King of the Hill/)).toBeInTheDocument()
  })

  it('affiche qui défie qui, et non seulement qui rencontre qui', async () => {
    // ⚠️ **Le cœur du format.** Une ligne « MARTIN vs DURAND » serait lisible et perdrait
    // l'information : c'est la position basse qui défie, et c'est elle qui monte si elle gagne.
    monter(<VueCollinePublique tournoiId={1} phaseId={9} />)

    expect(await screen.findByText(/le 2 défie le 1/)).toBeInTheDocument()
  })

  it('nomme les archers au repos plutôt que de les faire disparaître', async () => {
    // ⚠️ **Ce n'est pas le bye du suisse** : personne ne marque et personne ne bouge. Et ce n'est
    // pas un cas limite d'effectif impair — à portée 1, ce sont les deux extrémités une manche sur
    // deux. Sans cette ligne, un spectateur cherche son archer dans une liste où il ne peut pas
    // être et croit à un oubli d'appariement.
    vi.mocked(getEtatColline).mockResolvedValue(
      etat({ manches: [manche({ numero: 1, au_repos: [PETIT] })] }),
    )

    monter(<VueCollinePublique tournoiId={1} phaseId={9} />)

    expect(await screen.findByText(/PETIT/)).toBeInTheDocument()
    expect(screen.getByText(/personne ne marque/)).toBeInTheDocument()
  })

  it('filtre les archers au repos comme le reste en mode « mes archers »', async () => {
    // ⚠️ **Le défaut exact que la revue d'E05US031 a trouvé sur le bye du suisse**, évité ici : il
    // était rendu inconditionnellement, si bien qu'en « mes archers » le nom d'un archer non suivi
    // s'affichait quand même. L'interrupteur d'ADR-0079 vaut « sans exception ».
    vi.mocked(getEtatColline).mockResolvedValue(
      etat({ manches: [manche({ numero: 1, au_repos: [PETIT] })] }),
    )

    monter(<VueCollinePublique tournoiId={1} phaseId={9} mode="suivis" suivis={[1]} />)

    expect(await screen.findByText(/le 2 défie le 1/)).toBeInTheDocument()
    expect(screen.queryByText(/PETIT/)).toBeNull()
  })

  it('accorde le verbe sur les archers RÉELLEMENT affichés, pas sur la liste entière', async () => {
    // ⚠️ **Quatre axes de revue ont trouvé ce défaut indépendamment, et aucune fixture existante ne
    // pouvait l'atteindre** : le test ci-dessus n'a qu'un seul archer au repos, et sa liste filtrée
    // est vide — le bloc n'est donc même pas rendu. Il faut deux archers au repos dont **un seul**
    // suivi pour que l'écart se voie, et c'est le régime ordinaire du format : à portée 1, les deux
    // extrémités se reposent une manche sur deux. L'accord se lisait sur `manche.au_repos` (deux
    // noms) alors que le rendu ne montrait que `auReposSuivis` (un nom) → « PETIT Jo ne tire**nt**
    // pas cette manche ».
    vi.mocked(getEtatColline).mockResolvedValue(
      etat({ manches: [manche({ numero: 1, au_repos: [PETIT, DURAND] })] }),
    )

    monter(<VueCollinePublique tournoiId={1} phaseId={9} mode="suivis" suivis={[2]} />)

    // La ligne « au repos » est ciblée par sa classe : DURAND figure aussi dans un défi du décor,
    // et une recherche par texte sur toute la page ramènerait les deux.
    const auRepos = await screen.findByText(/ne tire/)

    expect(auRepos).toHaveTextContent(/DURAND/)
    expect(auRepos).not.toHaveTextContent(/PETIT/)
    // L'assertion qui porte le correctif : singulier, parce qu'UN seul nom est affiché.
    expect(auRepos).toHaveTextContent(/ne tire pas cette manche/)
    expect(auRepos).not.toHaveTextContent(/ne tirent pas/)
  })

  it('dit qu’aucun archer suivi ne tire ici plutôt que de rendre une manche vide', async () => {
    // ⚠️ « Aucun de vos archers ici » ≠ « manche vide » (ADR-0079) : l'archer suivi peut tirer dans
    // une autre phase, ou se reposer.
    monter(<VueCollinePublique tournoiId={1} phaseId={9} mode="suivis" suivis={[99]} />)

    expect(await screen.findByText(/Aucun des archers que vous suivez/)).toBeInTheDocument()
  })

  it('annonce les cibles manquantes au lieu de les taire', async () => {
    // Le second défaut trouvé en revue sur le suisse : les défis s'affichaient sans cible et le
    // spectateur croyait à un oubli. On **rapporte**, on ne comble pas (ADR-0083 §3).
    //
    // ⚠️ **L'assertion porte sur le SUJET de la phrase, et pas seulement sur sa fin** (correctif de
    // revue, deux axes). Elle disait `/pas encore de cibles attribuées/` — une regex qui ne touchait
    // pas le début du message, donc restait verte sur « **Un défi** n'a pas encore de cibles » alors
    // qu'une colline pose **un bloc unique pour toute la phase** : quand il manque, ce sont tous les
    // défis qui sont sans couloir, et l'organisateur doit comprendre qu'il a un plan à générer.
    vi.mocked(getEtatColline).mockResolvedValue(
      etat({ conflits: [{ groupe: 1, raison: 'non_posee' }] }),
    )

    monter(<VueCollinePublique tournoiId={1} phaseId={9} />)

    // ⚠️ Et le message **n'affirme pas la cause** (correctif de 2ᵉ passe) : `_PLAN_A_REPOSER`
    // couvre « jamais posé » ET « posé mais devenu trop court ». L'assertion porte donc sur le
    // constat et sur le fait que les deux causes sont nommées, jamais sur une seule d'entre elles —
    // sans quoi elle figerait un message qui envoie l'organisateur refaire un geste déjà fait.
    expect(await screen.findByText(/n’ont pas encore de cible/)).toBeInTheDocument()
    expect(screen.getByText(/le plan n’est pas posé, ou il ne couvre plus/)).toBeInTheDocument()
    expect(screen.queryByText(/^Un défi/)).toBeNull()
  })

  it('laisse remonter l’historique des manches', async () => {
    monter(<VueCollinePublique tournoiId={1} phaseId={9} />)

    await userEvent.click(await screen.findByRole('button', { name: 'Manche 1' }))

    expect(screen.getByText(/Manche 1 sur 3/)).toBeInTheDocument()
  })

  it('n’offre aucune navigation sur l’écran de salle', async () => {
    // CA E07US004 : l'écran projeté n'a personne pour cliquer, et un bouton inerte y est du bruit.
    monter(<VueCollinePublique tournoiId={1} phaseId={9} interactif={false} />)

    await screen.findByText(/Manche 2 sur 3/)
    expect(screen.queryByRole('button', { name: 'Manche 1' })).toBeNull()
  })

  it('explique l’attente sous la manche courante, et seulement là', async () => {
    monter(<VueCollinePublique tournoiId={1} phaseId={9} />)

    expect(await screen.findByText(/la manche 3 sera appariée/)).toBeInTheDocument()

    // ⚠️ Remonter l'historique **retire** la phrase : « en attente de la manche 3 » sous la manche 1
    // est vrai mais incompréhensible à cet endroit.
    await userEvent.click(screen.getByRole('button', { name: 'Manche 1' }))
    expect(screen.queryByText(/la manche 3 sera appariée/)).toBeNull()
  })

  it('dit que la première manche n’est pas encore appariée plutôt que de rester vide', async () => {
    vi.mocked(getEtatColline).mockResolvedValue(etat({ manches: [] }))

    monter(<VueCollinePublique tournoiId={1} phaseId={9} />)

    expect(await screen.findByText(/pas encore appariée/)).toBeInTheDocument()
  })
})
