// Écran des départs en tableau, état en colonne (E00US016, CA « liste/fiche »).

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErreurApi } from '../../shared/api/client'
import { Departs } from './Departs'

const mutation = () => ({ mutate: vi.fn(), isPending: false, error: null })
const { suppression } = vi.hoisted(() => ({
  suppression: { mutate: vi.fn(), reset: vi.fn(), isPending: false, error: null as Error | null },
}))

vi.mock('./hooks', () => ({
  useDeparts: () => ({
    isError: false,
    data: [
      {
        id: 1,
        tournoi_id: 1,
        numero: 1,
        horaire: '09:00',
        tarif_centimes: 810,
        quota: null,
        etat: 'lance',
      },
      {
        id: 2,
        tournoi_id: 1,
        numero: 2,
        horaire: '14:00',
        tarif_centimes: 0,
        quota: 20,
        etat: 'ouvert',
      },
    ],
  }),
  useCreerDepart: () => mutation(),
  useModifierDepart: () => mutation(),
  useSupprimerDepart: () => suppression,
}))

afterEach(() => {
  suppression.error = null
  suppression.mutate.mockClear()
})

const cellulesDe = (libelle: string) =>
  within(
    within(screen.getByRole('table'))
      .getByRole('cell', { name: libelle })
      .closest('tr') as HTMLElement,
  )
    .getAllByRole('cell')
    .map((td) => td.textContent)

describe('Départs — tableau', () => {
  it('donne sa colonne à l’état, à côté de l’horaire, du tarif et du quota', () => {
    render(<Departs tournoiId={1} />)

    expect(
      within(screen.getByRole('table'))
        .getAllByRole('columnheader')
        .map((th) => th.textContent),
    ).toEqual(['Départ', 'État', 'Horaire', 'Tarif', 'Quota', 'Actions'])
    expect(cellulesDe('Départ 1').slice(0, 5)).toEqual([
      'Départ 1',
      'Lancé',
      '09:00',
      '8,10 €',
      'sans plafond',
    ])
    expect(cellulesDe('Départ 2').slice(0, 5)).toEqual([
      'Départ 2',
      'Ouvert',
      '14:00',
      'Gratuit',
      '20',
    ])
  })

  it('« Éditer » remplace la ligne par le formulaire pré-rempli', async () => {
    render(<Departs tournoiId={1} />)

    await userEvent.click(screen.getByRole('button', { name: 'Éditer le départ 2' }))

    expect(
      within(screen.getByRole('table')).getByLabelText("Quota d'inscrits du départ"),
    ).toHaveValue('20')
  })

  it('le signalement d’une session de tir s’affiche sous sa ligne, avec son « quand même »', async () => {
    suppression.error = new ErreurApi(
      409,
      'depart_en_cours_non_confirme',
      'Le départ 1 est lancé : 12 archers ont tiré.',
    )
    render(<Departs tournoiId={1} />)

    const depart1 = screen.getByRole('cell', { name: 'Départ 1' }).closest('tbody') as HTMLElement
    const alerte = within(depart1).getByRole('alert')
    expect(alerte).toHaveTextContent('12 archers ont tiré')
    await userEvent.click(
      within(alerte).getByRole('button', { name: 'Supprimer quand même (session de tir)' }),
    )
    expect(suppression.mutate).toHaveBeenCalledWith({ departId: 1, confirmeCycle: true })
  })
})
