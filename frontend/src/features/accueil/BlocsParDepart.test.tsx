// Tests des blocs par départ de l'accueil (E16US021).
//
// Écrits **depuis le CA**, pas depuis le rendu : « un bloc par départ, tous visibles côte à côte et
// non un à la fois » — c'est le point qui distingue l'accueil de « Suivi du déroulé », qui n'en
// montre qu'un via un sélecteur. Et « chaque créneau porte ce qui sert à le dérouler » : l'effectif
// est celui **du créneau**, jamais celui du tournoi (ADR-0075).

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, expect, it, vi } from 'vitest'
import type { Depart } from '../departs/api'
import { getDeparts } from '../departs/api'
import { getArretsEnAttente } from '../suivi-deroule/api'
import { BlocsParDepart } from './BlocsParDepart'

vi.mock('../departs/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../departs/api')>()),
  getDeparts: vi.fn(),
}))
vi.mock('../suivi-deroule/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../suivi-deroule/api')>()),
  getArretsEnAttente: vi.fn(),
}))

function depart(partiel: Partial<Depart> = {}): Depart {
  return {
    id: 1,
    tournoi_id: 1,
    numero: 1,
    horaire: '09:00',
    tarif_centimes: 810,
    quota: null,
    etat: 'ouvert',
    effectif: 0,
    ...partiel,
  }
}

function enveloppe() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

beforeEach(() => {
  vi.mocked(getArretsEnAttente).mockResolvedValue([])
})

it('rend un bloc par départ, tous ensemble', async () => {
  vi.mocked(getDeparts).mockResolvedValue([
    depart({ id: 1, numero: 1, horaire: '09:00', effectif: 34 }),
    depart({ id: 2, numero: 2, horaire: '14:00', effectif: 12 }),
    depart({ id: 3, numero: 3, horaire: '17:30', effectif: 0 }),
  ])
  render(<BlocsParDepart tournoiId={1} />, { wrapper: enveloppe() })

  // Les trois sont présents **en même temps** : c'est la lettre du CA, et ce qu'un sélecteur de
  // créneau (`ChoixCreneau`, écran « Suivi du déroulé ») ne permettrait pas.
  expect(await screen.findByText('09:00')).toBeInTheDocument()
  expect(screen.getByText('14:00')).toBeInTheDocument()
  expect(screen.getByText('17:30')).toBeInTheDocument()
  expect(screen.getAllByRole('listitem')).toHaveLength(3)
})

it("chiffre l'effectif de chaque créneau, et le compare à son quota", async () => {
  vi.mocked(getDeparts).mockResolvedValue([
    depart({ id: 1, numero: 1, effectif: 34, quota: 40 }),
    depart({ id: 2, numero: 2, horaire: '14:00', effectif: 12, quota: null }),
  ])
  render(<BlocsParDepart tournoiId={1} />, { wrapper: enveloppe() })

  // Un quota se lit contre l'effectif **de son créneau**. Sans quota, le chiffre reste seul :
  // inventer un dénominateur (le total du tournoi) est le défaut qu'ADR-0075 a mis treize mois à
  // révéler — 34/120 ferait croire à un créneau au tiers plein.
  expect(await screen.findByText('34/40')).toBeInTheDocument()
  expect(screen.getByText('12')).toBeInTheDocument()
})

it('annonce la pause sur le créneau qui est à l’arrêt, pas sur les autres', async () => {
  vi.mocked(getDeparts).mockResolvedValue([
    depart({ id: 1, numero: 1 }),
    depart({ id: 2, numero: 2, horaire: '14:00' }),
  ])
  vi.mocked(getArretsEnAttente).mockImplementation((departId: number) =>
    Promise.resolve(
      departId === 2
        ? [
            {
              id: 9,
              phase_id: 3,
              apres_tour: 2,
              portee: 'depart' as const,
              phases_arretees: [3],
              arrete_depuis: null,
            },
          ]
        : [],
    ),
  )
  render(<BlocsParDepart tournoiId={1} />, { wrapper: enveloppe() })

  // Une seule annonce, et sur le bon bloc : c'est ce que la pastille globale qu'ils remplacent ne
  // savait pas faire — elle disait « une phase attend » sans dire de quel créneau.
  const annonces = await screen.findAllByRole('status')
  expect(annonces).toHaveLength(1)
  expect(annonces[0]).toHaveTextContent('Une phase attend votre relance')
})

it('garde les créneaux lisibles quand la lecture des pauses échoue', async () => {
  vi.mocked(getDeparts).mockResolvedValue([depart({ effectif: 34 })])
  vi.mocked(getArretsEnAttente).mockRejectedValue(new Error('réseau'))
  render(<BlocsParDepart tournoiId={1} />, { wrapper: enveloppe() })

  // `P-3` : la pause est la donnée la plus accessoire du bloc. Un hoquet dessus ne doit pas
  // emporter l'horaire et l'effectif, qui eux sont déjà arrivés.
  expect(await screen.findByText('34')).toBeInTheDocument()
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})

it('porte l’état de chaque créneau en toutes lettres', async () => {
  vi.mocked(getDeparts).mockResolvedValue([
    depart({ id: 1, numero: 1, etat: 'ouvert' }),
    depart({ id: 2, numero: 2, horaire: '14:00', etat: 'lance' }),
    depart({ id: 3, numero: 3, horaire: '17:30', etat: 'clos' }),
  ])
  render(<BlocsParDepart tournoiId={1} />, { wrapper: enveloppe() })

  // `DV-03` — le mot porte le sens, le liseré ne fait que le renforcer. L'état est l'une des cinq
  // données de l'énumération CA, et la plus facile à perdre en silence : un `<span>` retiré, ou un
  // `EtatDepart` renommé côté serveur, ne casserait aucun autre test.
  expect(await screen.findByText('à lancer')).toBeInTheDocument()
  expect(screen.getByText('en cours')).toBeInTheDocument()
  expect(screen.getByText('clos')).toBeInTheDocument()
})

it('signale un effectif au-delà du quota, sans se contenter d’une couleur', async () => {
  // Un quota abaissé sous les inscriptions déjà prises est atteignable : `ServiceDeparts.modifier`
  // ne les confronte pas. Le CA dit « se compare au quota » sans trancher le débordement — il se
  // signale donc, et par un MOT (`DV-03`), pas par la seule teinte.
  vi.mocked(getDeparts).mockResolvedValue([depart({ effectif: 45, quota: 40 })])
  render(<BlocsParDepart tournoiId={1} />, { wrapper: enveloppe() })

  expect(await screen.findByText('45/40')).toBeInTheDocument()
  expect(screen.getByText(/au-delà du quota/)).toBeInTheDocument()
})

it('garde les blocs affichés quand un rafraîchissement échoue', async () => {
  // `P-3` — une query qui a réussi puis dont un refetch échoue passe `isError` **en gardant
  // `data`**. Sur l'écran que l'organisateur laisse ouvert toute la journée, un hoquet du wifi de
  // salle ne doit pas effacer horaire, état, effectif et pause au profit d'un bandeau rouge.
  vi.mocked(getDeparts)
    .mockResolvedValueOnce([depart({ effectif: 34 })])
    .mockRejectedValue(new Error('réseau'))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const Enveloppe = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  render(<BlocsParDepart tournoiId={1} />, { wrapper: Enveloppe })
  expect(await screen.findByText('34')).toBeInTheDocument()

  await client.refetchQueries({ queryKey: ['departs', 1] })

  expect(client.getQueryState(['departs', 1])?.status).toBe('error')
  expect(screen.getByText('34')).toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})
