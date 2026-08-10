// Test de **rendu** de l'écran de saisie des poules (E05US023, ADR-0083).
//
// Il existe pour la même raison que son jumeau `SaisieDuels.test.tsx` : ce que cet écran **choisit
// d'appeler** ne se voit ni au typage ni au lint. Trois points le méritent ici :
//
// 1. le sélecteur ne doit proposer que les phases de type `poules` — proposer un tableau y
//    conduirait à un 409 `phase_pas_des_poules` sans qu'aucun test de logique pure ne le voie ;
// 2. les rencontres doivent être groupées **par tour**, c'est ce qui garantit qu'un tour se tire en
//    parallèle sur le bloc de couloirs de la poule ;
// 3. l'**annonce de barrage** doit apparaître sur la poule concernée, et sur elle seule — c'est la
//    seule surface qui la porte (le CA « le barrage se tire et se saisit »).
//
// On double uniquement les hooks de données ; le JSX est celui de production.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import type { EtatPoulesSaisie } from './api'
import { SaisiePoules } from './SaisiePoules'

const PHASES = [
  { id: 901, ordre: 1, type: 'qualification' },
  { id: 902, ordre: 2, type: 'poules' },
  { id: 903, ordre: 3, type: 'elimination_directe' },
]

vi.mock('../departs/api', () => ({
  getDeparts: () => Promise.resolve([{ id: 41, numero: 1, horaire: '09:00', etat: 'en_cours' }]),
}))

vi.mock('../saisie-duels/hooks', () => ({
  usePhases: (departId: number | null) => ({
    data: departId === null ? undefined : PHASES,
    isError: false,
    isSuccess: departId !== null,
    error: null,
  }),
  clePoules: (tournoiId: number, phaseId: number) => ['poules-etat', tournoiId, phaseId],
  useSaisirManche: () => MUTATION,
  useSaisirBarrage: () => MUTATION,
  useValiderDuel: () => MUTATION,
}))

vi.mock('./hooks', () => ({
  useEtatPoulesSaisie: () => ({ isPending: false, isError: false, data: ETAT, error: null }),
}))

const MUTATION = { mutate: vi.fn(), isPending: false, isError: false, error: null }

function duel(numero: number, hautNom: string, basNom: string) {
  return {
    numero,
    tour: 0,
    place_en_jeu: null,
    haut: { archer_id: numero * 10, nom: hautNom, prenom: 'P' },
    bas: { archer_id: numero * 10 + 1, nom: basNom, prenom: 'P' },
    est_bye: false,
    mode: 'sets' as const,
    nb_manches: 5,
    nb_fleches_par_volee: 3,
    points_pour_gagner: 6,
    zones: ['10', '9'],
    validee_par: null,
    manches: [],
    barrage: null,
    resultat: null,
  }
}

const ETAT: EtatPoulesSaisie = {
  phase_id: 902,
  repartition: { effectif: 6, taille_visee: 3, nb_poules: 2, tailles: [3, 3] },
  poules: [
    {
      numero: 1,
      membres: [
        { archer_id: 10, nom: 'DURAND', prenom: 'P' },
        { archer_id: 11, nom: 'LEFEVRE', prenom: 'P' },
      ],
      bloc: [
        [1, 'A'],
        [1, 'B'],
      ],
      rencontres: [
        { numero: 1, poule: 1, tour: 1, couloirs: null, duel: duel(1, 'DURAND', 'LEFEVRE') },
        { numero: 2, poule: 1, tour: 2, couloirs: null, duel: duel(2, 'DURAND', 'MOREAU') },
      ],
      classement: [
        {
          rang: 1,
          archer_id: 10,
          points_match: 3,
          diff_sets: 2,
          diff_score: 12,
          nb_dix: 1,
          nb_neuf: 2,
          ex_aequo: false,
        },
      ],
      qualifies: [],
      barrage_requis: true,
    },
    {
      numero: 2,
      membres: [{ archer_id: 20, nom: 'PETIT', prenom: 'P' }],
      bloc: null,
      rencontres: [
        { numero: 3, poule: 2, tour: 1, couloirs: null, duel: duel(3, 'PETIT', 'ROUX') },
      ],
      classement: [],
      qualifies: [],
      barrage_requis: false,
    },
  ],
  conflits: [],
}

function monter() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return render(<SaisiePoules tournoiId={1} />, { wrapper: Enveloppe })
}

async function choisirLaPhase() {
  monter()
  const selecteur = await screen.findByLabelText('Phase de poules à scorer')
  await userEvent.selectOptions(selecteur, '902')
  return selecteur
}

describe('SaisiePoules', () => {
  it('ne propose que les phases de poules du créneau', async () => {
    const selecteur = await choisirLaPhase()
    const proposees = Array.from(selecteur.querySelectorAll('option')).map((o) => o.textContent)

    // Ni la qualification (ordre 1) ni le tableau (ordre 3) : le serveur les refuserait en 409, et
    // y arriver par mégarde n'apporte qu'un message d'erreur à un scoreur qui n'y peut rien.
    expect(proposees).toEqual(['Choisir une phase…', 'Phase 2 — poules'])
  })

  it('présente les rencontres groupées par tour', async () => {
    await choisirLaPhase()

    // La poule 1 a une rencontre au tour 1 et une au tour 2 ; la poule 2 une au tour 1. Trois
    // en-têtes de tour au total, donc — le groupement est **par poule puis par tour**.
    expect(await screen.findAllByText(/^Tour \d$/)).toHaveLength(3)
  })

  it('annonce le barrage sur la poule qui le réclame, et sur elle seule', async () => {
    await choisirLaPhase()

    // CA « le barrage se tire et se saisit » : l'écran doit le **dire**, et dire où le tirer.
    const annonces = await screen.findAllByText(/Barrage requis/)
    expect(annonces).toHaveLength(1)
    expect(annonces[0]?.textContent).toContain('Départager les archers')
  })

  it('ouvre le pavé de saisie de duel sur une rencontre', async () => {
    await choisirLaPhase()
    await userEvent.click(await screen.findByText(/DURAND P contre LEFEVRE P/))

    // Le pavé est celui d'E04US013 — mêmes mots, mêmes gestes : une rencontre *est* un duel
    // ordinaire (ADR-0083 §7), et le scoreur n'a rien de neuf à apprendre.
    expect(await screen.findByText(/Enregistrer la manche/)).toBeInTheDocument()
    expect(screen.getByText(/Poule 1 · tour 1/)).toBeInTheDocument()
  })
})
