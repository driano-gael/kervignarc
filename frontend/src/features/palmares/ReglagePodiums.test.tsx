// Tests du panneau de réglage des podiums (E16US014).
//
// Ce qui se vérifie ici est ce que le composant **envoie** : la règle vit côté serveur, l'écran ne
// doit ni la deviner ni la doubler. Trois comportements, tous dérivés du CA — les portées se
// cumulent, aucune est valide, et la profondeur n'est envoyée qu'une fois la saisie finie.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getReglagePodiums, putReglagePodiums } from './api'
import { ReglagePodiums } from './ReglagePodiums'

vi.mock('./api', () => ({
  getReglagePodiums: vi.fn(),
  putReglagePodiums: vi.fn(),
}))

function Cadre({ enfants }: { enfants: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{enfants}</QueryClientProvider>
}

describe('ReglagePodiums', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getReglagePodiums).mockResolvedValue({ portees: ['categorie'], profondeur: 4 })
    vi.mocked(putReglagePodiums).mockResolvedValue({ portees: ['categorie'], profondeur: 4 })
  })

  /** Rend le panneau et attend que le réglage **du serveur** soit affiché.
   *
   * Sans cette attente, le clic tombe pendant que la lecture est en vol : les portées valent
   * encore `[]` et le composant enverrait un réglage calculé sur du vide. Le test passerait pour
   * un défaut du composant ce qui n'est qu'une course du harnais. */
  async function panneauCharge() {
    render(<Cadre enfants={<ReglagePodiums tournoiId={7} />} />)
    const categorie = await screen.findByRole('checkbox', { name: /Par catégorie/ })
    await waitFor(() => expect(categorie).toBeChecked())
    return categorie
  }

  it('ajoute une portée sans retirer celle qui est déjà cochée', async () => {
    // Le CA dit « cumulables » : cocher *club* alors que *catégorie* l'est doit envoyer les deux.
    // Un composant qui traiterait les portées comme un choix unique passerait ce test à l'envers.
    await panneauCharge()
    const club = screen.getByRole('checkbox', { name: /Par club/ })

    fireEvent.click(club)

    await waitFor(() =>
      expect(putReglagePodiums).toHaveBeenCalledWith(7, {
        portees: ['categorie', 'club'],
        profondeur: 4,
      }),
    )
  })

  it('accepte de tout décocher — ne rien récompenser est un réglage', async () => {
    const categorie = await panneauCharge()

    fireEvent.click(categorie)

    await waitFor(() =>
      expect(putReglagePodiums).toHaveBeenCalledWith(7, { portees: [], profondeur: 4 }),
    )
  })

  it('n’envoie la profondeur qu’une fois la saisie terminée', async () => {
    // À chaque frappe, « 12 » passe par « 1 » : envoyer à `onChange` aurait fait retenir un podium
    // à une place si l'organisateur s'arrêtait là.
    await panneauCharge()
    const champ = screen.getByLabelText('Places récompensées')

    fireEvent.change(champ, { target: { value: '1' } })
    fireEvent.change(champ, { target: { value: '12' } })
    expect(putReglagePodiums).not.toHaveBeenCalled()
    fireEvent.blur(champ)

    await waitFor(() =>
      expect(putReglagePodiums).toHaveBeenCalledWith(7, {
        portees: ['categorie'],
        profondeur: 12,
      }),
    )
  })
})
