// Tests du réglage « jusqu'où classer » sur l'écran de composition (E06US006, ADR-0070).
//
// Trois choses s'y jouent, et chacune ferme un piège de l'US :
//
// 1. **Le réglage n'apparaît que sur un tableau.** Une poule ou un échauffement n'a pas d'arbre à
//    tronquer ; l'offrir mènerait à un 422 dont la consigne n'est pas réalisable à l'écran ;
// 2. **« Ne rien régler » reste distinct de « podium 4 »**, alors que les deux produisent le même
//    tournoi. Les confondre écrirait un réglage sur chaque phase déjà composée et ferait passer un
//    défaut hérité pour un choix de l'organisateur ;
// 3. **Un top N sans rang d'arrêt ne part pas au serveur.** Le domaine le refuse ; l'écran le dit
//    avant, plutôt que de renvoyer un 422 illisible.

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { FormulaireEtape } from './Deroule'

// Matcher volontairement court : le libellé mêle apostrophes droites et typographiques selon les
// écrans, et un test qui casse sur une apostrophe ne dit rien de la fonctionnalité.
const CHOIX = /classer/

function poser(type: 'elimination_directe' | 'poules' = 'elimination_directe') {
  const surValider = vi.fn()
  render(
    <FormulaireEtape
      etape={{
        ordre: 1,
        type,
        bareme: null,
        validation: null,
        sources: [],
        effectif: null,
        profondeur: null,
      }}
      etapesAmont={[]}
      surValider={surValider}
      surAnnuler={() => {}}
    />,
  )
  return surValider
}

describe('profondeur de classement', () => {
  it('ne propose le réglage que sur une phase en tableau', () => {
    poser('poules')

    expect(screen.queryByLabelText(CHOIX)).toBeNull()
  })

  it('laisse la phase au preset tant qu’on ne choisit rien', async () => {
    const surValider = poser()

    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))

    // `null`, et non `{ nom: 'podium', jusqu_au: 4 }` : le serveur distingue « non réglée » de
    // « réglée au podium », et seule la première laisse la phase suivre son preset.
    expect(surValider).toHaveBeenCalledWith(expect.objectContaining({ profondeur: null }))
  })

  it('transmet le classement intégral sans rang d’arrêt', async () => {
    const surValider = poser()

    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'un_vers_n')
    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))

    expect(surValider).toHaveBeenCalledWith(
      expect.objectContaining({ profondeur: { nom: 'un_vers_n', jusqu_au: null } }),
    )
  })

  it('transmet le rang d’arrêt d’un top N', async () => {
    const surValider = poser()

    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'podium')
    const seuil = screen.getByLabelText(/Dernier rang départagé/)
    await userEvent.clear(seuil)
    await userEvent.type(seuil, '8')
    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))

    expect(surValider).toHaveBeenCalledWith(
      expect.objectContaining({ profondeur: { nom: 'podium', jusqu_au: 8 } }),
    )
  })

  it('refuse de valider un top N dont le rang d’arrêt est vide', async () => {
    const surValider = poser()

    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'podium')
    const seuil = screen.getByLabelText(/Dernier rang départagé/)
    await userEvent.clear(seuil)

    expect(screen.getByRole('button', { name: 'Valider' })).toHaveProperty('disabled', true)
    // `DV-03` : le blocage est **dit**, jamais seulement subi par un bouton grisé.
    expect(screen.getByRole('status').textContent).toContain('rang où le classement')
    expect(surValider).not.toHaveBeenCalled()
  })

  it('oublie le réglage si la phase cesse d’être un tableau', async () => {
    const surValider = poser()

    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'un_vers_n')
    await userEvent.selectOptions(screen.getByLabelText(/Type de phase/), 'poules')
    await userEvent.click(screen.getByRole('button', { name: 'Valider' }))

    // Sans cet oubli, retyper une phase enverrait une profondeur que le serveur refuse (422) —
    // sur un réglage devenu invisible, donc impossible à corriger depuis l'écran.
    expect(surValider).toHaveBeenCalledWith(expect.objectContaining({ profondeur: null }))
  })
})
