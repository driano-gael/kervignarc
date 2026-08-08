// Tests de **montage** de la table de classement (E06US001, élargie par E16US004).
//
// Ce fichier naît d'un défaut de **conjonction** trouvé en revue d'E16US004, du genre que ni les
// tests de logique pure ni les tests d'architecture ne peuvent voir, parce qu'il n'existe qu'à la
// jonction de deux moitiés vertes :
//
//  - `focus.centrerLignes` filtrait correctement (testé, conforme au CA « on ne renumérote pas ») ;
//  - `departage.totauxExAequo` calculait correctement (testé sur listes complètes) ;
//  - et pourtant, branchés l'un sur l'autre, ils **effaçaient une égalité FFTA** de l'écran le plus
//    regardé de la journée : le calcul recevait la liste déjà filtrée, si bien qu'un archer suivi à
//    542 points, à égalité avec un archer **non suivi** à 542, se retrouvait seul avec son total et
//    n'était plus signalé comme ex æquo. Son rang se présentait comme acquis alors qu'il tenait à
//    un départage au nombre de 10 — voire à un barrage encore à tirer.
//
// D'où la règle que ces tests verrouillent : **la source du calcul n'est pas la source de
// l'affichage**. `lignes` dit ce qu'on montre, `lignesCompletes` dit sur quoi l'on raisonne.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useDeroule } from '../suivi/deroule'
import type { LigneClassement } from './api'
import { TableClassement } from './TableClassement'

// ⚠️ On mocke **le hook**, pas `getDeroule` : `useDeroule` appelle la fonction par sa liaison
// **locale** au module, que le remplacement de l'export ne redirige pas — la vraie requête partait
// donc quand même, et le test lisait « connexion perdue ».
vi.mock('../suivi/deroule', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../suivi/deroule')>()),
  useDeroule: vi.fn(),
}))

// `LigneArcher` monte `usePlacerArcher` même en lecture seule : il faut un client, même inutilisé.
function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

function ligne(patch: Partial<LigneClassement> = {}): LigneClassement {
  return {
    rang_scratch: 23,
    rang_categorie: 5,
    archer_id: 1,
    nom: 'MARTIN',
    prenom: 'Luc',
    categorie_id: 3,
    categorie_libelle: 'Senior 1 Homme',
    cible: 7,
    club_id: 2,
    total: 542,
    nb_dix: 12,
    nb_neuf: 9,
    statut: 'en_lice',
    ...patch,
  }
}

// L'archer avec qui l'égalité existe : même catégorie, même total, un autre identifiant.
const RIVAL = ligne({ archer_id: 2, nom: 'DURAND', prenom: 'Eve', rang_scratch: 24, nb_dix: 8 })

describe('TableClassement — ex æquo et liste centrée', () => {
  it('signale l’ex æquo même quand l’archer à égalité est masqué par le centrage', () => {
    // Le cas réel : je suis MARTIN, pas DURAND. L'écran ne montre que MARTIN — mais son 542 est
    // toujours à égalité avec celui de DURAND, et le taire trompe sur la solidité de son rang.
    render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={[ligne()]}
            lignesCompletes={[ligne(), RIVAL]}
            admin={false}
          />
        }
      />,
    )

    expect(screen.getByText(/Ex æquo signalés/)).toBeInTheDocument()
  })

  it('ne signale rien quand l’égalité n’existe pas dans la liste complète', () => {
    // Symétrique indispensable : sans lui, le test précédent passerait aussi avec un composant qui
    // affiche la mention en permanence.
    render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={[ligne()]}
            lignesCompletes={[ligne(), ligne({ archer_id: 2, total: 500 })]}
            admin={false}
          />
        }
      />,
    )

    expect(screen.queryByText(/Ex æquo signalés/)).toBeNull()
  })

  it('n’annonce pas la règle quand l’égalité ne concerne aucune ligne affichée', () => {
    // ⚠️ Le piège du correctif lui-même (2ᵉ passe de revue). Calculer les égalités sur la liste
    // complète corrige le **marquage**, mais si l'on en déduit aussi l'**affichage** du paragraphe
    // de règle, celui-ci apparaît dès qu'une égalité existe quelque part dans le créneau — donc
    // quasiment en permanence — sous une table de trois lignes dont aucune n'est marquée.
    // `departage.ts` l'énonce : « encore faut-il montrer sur qui ».
    render(
      <Cadre
        enfants={
          <TableClassement
            tournoiId={1}
            lignes={[ligne()]}
            lignesCompletes={[
              ligne(),
              ligne({ archer_id: 2, total: 500 }),
              ligne({ archer_id: 3, total: 500 }),
            ]}
            admin={false}
          />
        }
      />,
    )

    // L'égalité existe (500 = 500) mais entre deux archers qu'on n'affiche pas : rien à annoncer.
    expect(screen.queryByText(/Ex æquo signalés/)).toBeNull()
  })

  it('se comporte comme avant quand aucune liste complète n’est fournie', () => {
    // Non-régression des appelants qui n'ont rien à centrer (admin, simulation, écran de salle) :
    // `lignesCompletes` est optionnelle et retombe sur `lignes`.
    render(
      <Cadre enfants={<TableClassement tournoiId={1} lignes={[ligne(), RIVAL]} admin={false} />} />,
    )

    expect(screen.getByText(/Ex æquo signalés/)).toBeInTheDocument()
  })
})

describe('TableClassement — détail des flèches (CA racine E16US004)', () => {
  beforeEach(() => {
    vi.mocked(useDeroule).mockReturnValue({
      data: {
        tournoi_id: 1,
        archer_id: 1,
        cumul: 542,
        volees: [
          { numero: 1, valeurs: ['10', '9', '9'], points: 28, statut: 'valide', horodatage: null },
        ],
      },
      isPending: false,
      isError: false,
      // Double cast **assumé** (règle 4-front) : le type de retour de React Query compte une
      // trentaine de champs dont aucun n'intervient ici. Les stubber tous rendrait le test moins
      // lisible sans rien prouver de plus ; c'est un double de test, pas une valeur de production.
    } as unknown as ReturnType<typeof useDeroule>)
  })

  it('déplie le détail au clavier et l’annonce au lecteur d’écran', async () => {
    // P03 demandait « le détail des flèches des autres » — réponse *« oui »*. C'est le livrable le
    // plus visible de l'US, et il n'avait aucun test : ~130 lignes de JSX, dont le contrat
    // d'accessibilité (`aria-expanded`, `aria-controls`) que rien ne vérifiait.
    //
    // Au **clavier**, délibérément : l'appli publique se consulte aussi au lecteur d'écran, et
    // c'est la raison invoquée pour préférer un vrai `<button>` à une rangée cliquable. Tester au
    // clic seul aurait laissé passer une régression vers `<tr onClick>`.
    const utilisateur = userEvent.setup()
    render(
      <Cadre
        enfants={<TableClassement tournoiId={1} lignes={[ligne()]} admin={false} detailFleches />}
      />,
    )

    const bascule = screen.getByRole('button', { name: /MARTIN/ })
    expect(bascule).toHaveAttribute('aria-expanded', 'false')

    bascule.focus()
    await utilisateur.keyboard('{Enter}')

    expect(bascule).toHaveAttribute('aria-expanded', 'true')
    await waitFor(() => expect(screen.getByText(/10 9 9/)).toBeInTheDocument())
    // La région dépliée est bien celle que le bouton déclare piloter.
    expect(bascule.getAttribute('aria-controls')).toBe(`detail-archer-${ligne().archer_id}`)

    await utilisateur.keyboard('{Enter}')
    expect(bascule).toHaveAttribute('aria-expanded', 'false')
  })

  it('n’expose aucun dépliant quand le détail n’est pas demandé', async () => {
    // L'admin a l'écran de saisie et la salle « aucune interaction » (CA E07US004) : la prop est
    // réservée à l'appli publique, et son défaut doit rester inerte.
    render(<Cadre enfants={<TableClassement tournoiId={1} lignes={[ligne()]} admin={false} />} />)

    expect(screen.queryByRole('button', { name: /MARTIN/ })).toBeNull()
  })
})
