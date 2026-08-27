// Test de **montage** de `VueClassement` — le maillon de câblage laissé nu (E16US009, revue).
//
// ⚠️ Le réglage de pages traverse quatre étages : `EcranSalle` → `VueDeSalle` → `VueClassement` →
// `TableClassement`. Les deux bouts étaient gardés (`teteFigee.test.ts`,
// `TableClassement.test.tsx`) ; le **milieu** ne l'était pas — retirer la prop `pagination`
// laissait toute la suite verte et ramenait la salle au cadre à ascenseur que personne ne peut
// actionner dans un gymnase. ADR-0098 §2 n'est garanti que **dans un sens** ; `tsc` est aveugle à
// une propriété fournie et jamais consommée (`DETTE-085`).

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useDeparts } from '../departs/hooks'
import type { LigneClassement } from './api'
import { useClassement } from './hooks'
import { VueClassement } from './VueClassement'

// On mocke **les hooks**, pas les fonctions de requête : `useDeparts`/`useClassement` appellent
// leur fabrique par sa liaison locale au module, que le remplacement de l'export ne redirige pas
// (même piège que dans `TableClassement.test.tsx`, où le test lisait « connexion perdue »).
vi.mock('./hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./hooks')>()),
  useClassement: vi.fn(),
}))
vi.mock('../departs/hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/hooks')>()),
  useDeparts: vi.fn(),
}))

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

function ligne(i: number): LigneClassement {
  return {
    rang_scratch: i + 1,
    rang_categorie: i + 1,
    archer_id: i + 1,
    nom: `ARCHER${i}`,
    prenom: 'Luc',
    categorie_id: 3,
    categorie_libelle: 'Senior 1 Homme',
    cible: 7,
    club_id: 2,
    total: 600 - i,
    nb_dix: 12,
    nb_neuf: 9,
    statut: 'en_lice',
  }
}

const DIX = Array.from({ length: 10 }, (_, i) => ligne(i))

describe('VueClassement — le réglage de pages atteint bien la table', () => {
  beforeEach(() => {
    vi.mocked(useDeparts).mockReturnValue({
      data: [{ id: 1, tournoi_id: 1, numero: 1, libelle: 'D1', debut: null, fin: null }],
      isSuccess: true,
      isPending: false,
      isError: false,
      // Double cast **assumé** (règle 4-front) : le retour de React Query compte une trentaine de
      // champs dont aucun n'intervient ici. C'est un double de test, pas une valeur de production.
    } as unknown as ReturnType<typeof useDeparts>)
    vi.mocked(useClassement).mockReturnValue({
      data: { lignes: DIX, egalites_a_departager: [] },
      isSuccess: true,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useClassement>)
  })

  it('bascule le reste en pages quand un réglage est fourni (écran de salle)', () => {
    const { container } = render(
      <Cadre
        enfants={
          <VueClassement
            tournoiId={1}
            admin={false}
            filtrable={false}
            pagination={{ noms_par_page: 12, cadence_page_s: 20 }}
          />
        }
      />,
    )

    // Le marqueur du rendu paginé — il n'existe que si `pagination` a traversé les deux étages.
    expect(container.querySelector('.classement__pages')).not.toBeNull()
    // Et surtout : **pas** de cadre à ascenseur, qui est la régression que l'ADR interdit.
    expect(container.querySelector('.classement__defilement')).toBeNull()
    // Le découpage est bien effectif : 12 noms réglés → 4 lignes par page, le 5ᵉ du reste attend.
    expect(container.textContent).not.toContain('ARCHER7 ')
  })

  it('rend le classement ENTIER quand aucun réglage n’est fourni', () => {
    // L'assertion **appariée**, et c'est le lien mécanique d'ADR-0098 §2 pris par son autre bout :
    // sans réglage de pages, `teteFigee` retombe à **zéro**, donc pas de tête figée, pas de pages —
    // le classement complet, comme avant l'US. On ne peut pas livrer par inadvertance « 3 lignes et
    // rien d'autre », qui serait une régression de ce que la salle affichait (revue du 05/08/2026).
    //
    // Sans ce test, le précédent passerait aussi avec un composant qui paginerait en toutes
    // circonstances.
    const { container } = render(
      <Cadre enfants={<VueClassement tournoiId={1} admin={false} filtrable={false} />} />,
    )

    expect(container.querySelector('.classement__pages')).toBeNull()
    // Ni pages, ni cadre à ascenseur : la tête figée étant nulle, il n'y a rien à séparer.
    expect(container.querySelector('.classement__defilement')).toBeNull()
    // Et **tout le monde** est rendu — rien n'est tronqué.
    expect(container.textContent).toContain('ARCHER9 ')
  })
})
