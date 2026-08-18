// Tests de **montage** de la vue publique du Big Shoot Off (E05US031, ADR-0089).
//
// ⚠️ **Ce fichier n'existait pas à la première passe de revue, et son absence a laissé passer un
// bloquant.** L'US avait livré quatre composants de vue neufs et n'en montait qu'un
// (`VueEnCours.test.tsx`), dont l'en-tête affirmait pourtant que « chacun a ses propres tests ».
// Le défaut trouvé en revue (axe C1) : l'en-tête affichait `format.restants` — le nombre d'archers
// qui resteront **à la fin** — sous le libellé « encore en lice ». Soit « 5 encore en lice » dès la
// première manche, avec 12 archers sur les cibles, et le chiffre ne bougeait pas de la finale.
// Aucune porte mécanique ne pouvait le voir (le DTO est conforme, le test d'API vérifie les clés) ;
// seul un rendu l'attrape. C'est mot pour mot le récit que porte `VueTableaux.test.tsx`.
//
// Les cas dérivent de `docs/fonctionnel/E05US031.md` § scénario 4 et du CA « mes archers », pas de
// l'implémentation.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EtatBigShootOffPublic, TireurPublic } from './api'
import { getEtatBigShootOff } from './api'
import { VueBigShootOffPublique } from './VueBigShootOffPublique'

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  getEtatBigShootOff: vi.fn(),
}))

function tireur(
  patch: Partial<TireurPublic> & Pick<TireurPublic, 'archer_id' | 'nom'>,
): TireurPublic {
  return { prenom: 'P', en_lice: true, rang: null, scores: [], ...patch }
}

/** Une finale « 12 → 8 → 6 → 5 » dont la première manche est jouée. */
function etat(patch: Partial<EtatBigShootOffPublic> = {}): EtatBigShootOffPublic {
  return {
    phase_id: 8,
    format: {
      effectif: 12,
      paliers: [8, 6, 5],
      restants: 5,
      volees: 3,
      fleches_par_volee: 3,
      manches_jouables: 3,
    },
    tireurs: [
      tireur({ archer_id: 1, nom: 'MARTIN', scores: [57] }),
      tireur({ archer_id: 2, nom: 'DURAND', scores: [55] }),
      tireur({ archer_id: 3, nom: 'PETIT', en_lice: false, rang: 9, scores: [41] }),
    ],
    manches: [
      { numero: 1, elimine: 4, complete: true, jouee: true },
      { numero: 2, elimine: 2, complete: false, jouee: false },
    ],
    termine: false,
    barrage: null,
    ...patch,
  }
}

function monter(noeud: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{noeud}</QueryClientProvider>)
}

beforeEach(() => vi.mocked(getEtatBigShootOff).mockReset())

describe('VueBigShootOffPublique — l’en-tête dit ce qui se passe maintenant', () => {
  it('compte les archers RÉELLEMENT en lice, pas ceux qui resteront à la fin', async () => {
    // ⚠️ **Le bloquant de la revue.** `format.restants` vaut 5 (le « K dérivé », `paliers[-1]`) ;
    // il en reste 2 en lice à cet instant. Afficher 5 annoncerait la fin de la finale dès sa
    // première manche — sur l'information même que cette vue existe pour donner.
    vi.mocked(getEtatBigShootOff).mockResolvedValue(etat())

    monter(<VueBigShootOffPublique tournoiId={1} phaseId={8} />)

    expect(await screen.findByText(/2 encore en lice/)).toBeInTheDocument()
    expect(screen.queryByText(/5 encore en lice/)).toBeNull()
  })

  it('annonce le chemin du format en partant de l’effectif de départ', async () => {
    // La fiche de recette (scénario 4) promet « 12 → 8 → 6 → 5 ». `paliers` ne porte que ce qu'il
    // reste **après** chaque manche : servi seul, il rendait « 8 → 6 → 5 » et la recette ne pouvait
    // pas passer.
    vi.mocked(getEtatBigShootOff).mockResolvedValue(etat())

    monter(<VueBigShootOffPublique tournoiId={1} phaseId={8} />)

    expect(await screen.findByText(/12 → 8 → 6 → 5/)).toBeInTheDocument()
  })

  it('n’ouvre une colonne que pour les manches jouées', async () => {
    // Le réglage peut dépasser l'effectif (`manches_ignorees`) : afficher les manches à venir ferait
    // lire une finale plus longue qu'elle ne sera.
    vi.mocked(getEtatBigShootOff).mockResolvedValue(etat())

    monter(<VueBigShootOffPublique tournoiId={1} phaseId={8} />)

    expect(await screen.findByRole('columnheader', { name: 'M1' })).toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'M2' })).toBeNull()
  })
})

describe('VueBigShootOffPublique — le sort de chaque finaliste', () => {
  it('ne rend jamais un zéro pour une manche non scellée', async () => {
    // Promesse explicite du scénario 4-3 : un tiret, jamais « 0 ». Un zéro inventé ferait croire à
    // un tir manqué sur un archer dont la feuille est simplement en cours de validation.
    vi.mocked(getEtatBigShootOff).mockResolvedValue(
      etat({ tireurs: [tireur({ archer_id: 1, nom: 'MARTIN', scores: [] })] }),
    )

    monter(<VueBigShootOffPublique tournoiId={1} phaseId={8} />)

    const ligne = await screen.findByRole('row', { name: /MARTIN/ })
    expect(ligne).toHaveTextContent('—')
    expect(ligne).not.toHaveTextContent('0')
  })

  it('dit « en lice » sans rang, et le rang une fois sorti', async () => {
    // `rang` est `null` tant que l'archer tire : un rang annoncé avant la sortie serait un faux
    // départ, et c'est le serveur qui tient cette règle.
    vi.mocked(getEtatBigShootOff).mockResolvedValue(etat())

    monter(<VueBigShootOffPublique tournoiId={1} phaseId={8} />)

    expect(await screen.findByRole('row', { name: /MARTIN/ })).toHaveTextContent('en lice')
    expect(screen.getByRole('row', { name: /PETIT/ })).toHaveTextContent('9ᵉ')
  })

  it('annonce le barrage qui suspend la phase', async () => {
    // Sans ce mot, la salle voit une manche validée qui n'élimine personne et rien ne l'explique.
    vi.mocked(getEtatBigShootOff).mockResolvedValue(
      etat({ barrage: { archer_ids: [1, 2], noms: ['P MARTIN', 'P DURAND'], places: 1 } }),
    )

    monter(<VueBigShootOffPublique tournoiId={1} phaseId={8} />)

    expect(await screen.findByText(/Barrage en cours entre/)).toHaveTextContent('une place')
  })
})

describe('VueBigShootOffPublique — « mes archers » (ADR-0079)', () => {
  it('nomme « aucun de vos archers ici » distinctement de son propre vide', async () => {
    // Les deux branches disent deux choses différentes : « pas encore de finalistes » est un état
    // du tournoi, « aucun des vôtres » est un état du filtre.
    vi.mocked(getEtatBigShootOff).mockResolvedValue(etat())

    monter(<VueBigShootOffPublique tournoiId={1} phaseId={8} mode="suivis" suivis={[99]} />)

    expect(await screen.findByText(/Aucun des archers que vous suivez/)).toBeInTheDocument()
    expect(screen.queryByText(/pas encore connus/)).toBeNull()
  })

  it('ne filtre pas le compte « en lice » sur les archers suivis', async () => {
    // Le total décrit la finale, pas la sélection : le faire dépendre de qui l'on suit rendrait
    // l'en-tête faux pour tout le monde sauf soi.
    vi.mocked(getEtatBigShootOff).mockResolvedValue(etat())

    monter(<VueBigShootOffPublique tournoiId={1} phaseId={8} mode="suivis" suivis={[1]} />)

    expect(await screen.findByText(/2 encore en lice/)).toBeInTheDocument()
  })
})
